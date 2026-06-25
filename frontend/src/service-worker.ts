// Disables access to DOM typings like `HTMLElement` which are not available
// inside a service worker and instantiates the correct globals
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

// Ensures that the `$service-worker` import has proper type definitions
/// <reference types="@sveltejs/kit" />

// Only necessary if you have an import from `$env/static/public`
/// <reference types="../.svelte-kit/ambient.d.ts" />

import { PUBLIC_API_URL } from '$env/static/public';
import { build, files, version } from '$service-worker';

// This gives `self` the correct types
const self = globalThis.self as unknown as ServiceWorkerGlobalScope;

// The backend is deployed under a path on the *same* origin as the app
// (e.g. https://host/api), so an origin check can't tell API calls apart from
// the app shell. Derive the API's origin + base path from PUBLIC_API_URL and
// treat anything under it as network-only: the SW must never cache or replay
// user-specific, dynamic API data — the app's own IndexedDB layer owns offline
// caching, and a cached health/probe response would make us look online while
// the device is offline.
// PUBLIC_API_URL is relative by default (e.g. `/api`), so resolve it against
// this worker's own origin — `new URL` throws on a bare path without a base.
const API_URL = new URL(PUBLIC_API_URL, self.location.origin);
// Drop any trailing slash so the prefix match below is exact.
const API_BASE_PATH = API_URL.pathname.replace(/\/+$/, '');

function isApiRequest(url: URL): boolean {
	if (url.origin !== API_URL.origin) return false;
	return url.pathname === API_BASE_PATH || url.pathname.startsWith(`${API_BASE_PATH}/`);
}

interface PushNotificationPayload {
	title: string;
	body: string;
	url: string;
	// Set by the backend to `notification.id` — collapses re-pushes of the same
	// notification while keeping distinct notifications separate.
	tag?: string;
	// Set by the backend for self-test pushes. Forces the OS-level notification
	// even when the app is visible, so the user can verify push delivery without
	// backgrounding the app.
	test?: boolean;
}

interface NotificationClickData {
	url?: string;
}

async function hasVisibleAppClient() {
	const windowClients = await self.clients.matchAll({
		type: 'window',
		includeUncontrolled: true
	});

	return windowClients.some((client) => client.visibilityState === 'visible');
}

// Create a unique cache name for this deployment
const CACHE = `cache-${version}`;

// `build` lists the Vite-generated app files: empty during `vite dev` (the app is
// not bundled) and populated in production builds. We use that as a reliable dev
// signal to disable the fetch/caching handler in dev — its cache-first app shell
// goes stale across HMR rebuilds and serves an outdated shell on hard navigations,
// 404ing deep links the live dev server actually has. Push notifications still work
// in dev because the `push`/`notificationclick` handlers below stay registered.
const dev = build.length === 0;

const ASSETS = [
	...build, // the app itself
	...files // everything in `static`
];

self.addEventListener('install', (event) => {
	// Create a new cache and add all files to it
	async function addFilesToCache() {
		const cache = await caches.open(CACHE);
		await cache.addAll(ASSETS);

		// Precache the app-shell entry so an offline navigation to any never-visited
		// route can fall back to it (see the navigate handler below). Done separately
		// and tolerantly: a failure here must not abort the whole install.
		try {
			await cache.add('/');
		} catch {
			// Best-effort — the opportunistic cache.put in the fetch handler still
			// captures '/' on the first online visit.
		}
	}

	event.waitUntil(addFilesToCache());
});

self.addEventListener('activate', (event) => {
	async function activate() {
		// Remove previous cached data from disk
		for (const key of await caches.keys()) {
			if (key !== CACHE) await caches.delete(key);
		}
		// Take control of open pages immediately after a controlled update
		// (the in-app prompt reloads them on `controllerchange`).
		await self.clients.claim();
	}

	event.waitUntil(activate());
});

// The new worker waits by default so the user is never interrupted mid-session.
// The in-app "new version" prompt posts this message when the user accepts,
// which activates the waiting worker and triggers a reload.
self.addEventListener('message', (event) => {
	if (event.data === 'skipWaiting') {
		self.skipWaiting();
	}
});

self.addEventListener('fetch', (event) => {
	// In dev, never intercept: let every request hit the network (vite) directly so
	// the browser always gets a fresh shell. The cache-first strategy below assumes
	// an immutable, versioned shell — an invariant only production builds satisfy.
	if (dev) return;

	// ignore POST requests etc
	if (event.request.method !== 'GET') return;

	// Skip EventSource requests
	if (event.request.headers.get('Accept') === 'text/event-stream') return;

	// Never intercept API calls: let them hit the network directly so they fail
	// honestly when offline. Serving a cached API response here would falsely
	// report the server as reachable and replay stale data.
	if (isApiRequest(new URL(event.request.url))) return;

	async function respond() {
		const url = new URL(event.request.url);
		const cache = await caches.open(CACHE);

		// `build`/`files` can always be served from the cache
		if (ASSETS.includes(url.pathname)) {
			const response = await cache.match(url.pathname);

			if (response) {
				return response;
			}
		}

		// App-shell, cache-first: every route renders from the same client-built
		// shell, which is immutable per deploy and versioned by `version` (updates
		// ride the in-app prompt + skipWaiting, never the network). Serving the
		// precached shell for navigations means startup never depends on the
		// origin being healthy — a reachable-but-broken upstream (502/503/504) can
		// no longer block the app from booting, where a network-first navigation
		// would return the gateway error page instead.
		if (event.request.mode === 'navigate') {
			const shell = (await cache.match('/')) ?? (await cache.match('/200.html'));
			if (shell) {
				return shell;
			}
		}

		// for everything else, try the network first, but
		// fall back to the cache if we're offline
		try {
			const response = await fetch(event.request);

			// if we're offline, fetch can return a value that is not a Response
			// instead of throwing - and we can't pass this non-Response to respondWith
			if (!(response instanceof Response)) {
				throw new Error('invalid response from fetch');
			}

			// Only cache same-origin GETs (the app shell and static assets).
			// API calls (same origin under PUBLIC_API_URL's base path) are
			// filtered out before reaching here by `isApiRequest`, so they are
			// never stored — the app layer owns their offline caching.
			if (response.status === 200 && url.origin === self.location.origin) {
				cache.put(event.request, response.clone());
			}

			return response;
		} catch (err) {
			const response = await cache.match(event.request);

			if (response) {
				return response;
			}

			// SPA: every route renders from the same client-built app shell, so a
			// navigation to a URL we never cached (hard reload, deep link, or PWA
			// cold start while offline) can still boot from the cached entry doc
			// instead of hitting the browser's native error page.
			if (event.request.mode === 'navigate') {
				const shell = await cache.match('/');
				if (shell) {
					return shell;
				}
			}

			// if there's no cache, then just error out
			// as there is nothing we can do to respond to this request
			throw err;
		}
	}

	event.respondWith(respond());
});

// Push Notifications Handling
self.addEventListener('push', (event: PushEvent) => {
	let data: PushNotificationPayload = {
		title: 'ФАН ФАН',
		body: 'Новое уведомление',
		url: '/'
	};

	if (event.data) {
		try {
			// Try parsing as JSON first (expected format: { title, body, url })
			const json = event.data.json() as Partial<PushNotificationPayload>;
			data = { ...data, ...json };
		} catch {
			// Not JSON — treat as plain text body
			data.body = event.data.text();
		}
	}

	const options = {
		body: data.body,
		icon: '/favicon.png',
		badge: '/favicon.png',
		tag: data.tag,
		data: {
			url: data.url || '/'
		}
	};

	event.waitUntil(
		(async () => {
			// When the app is already visible, the user will see the in-app toast and bell update.
			// Skip the OS-level push notification to avoid duplicate alerts for the same message.
			// Test pushes are the exception: always show them so the user can confirm delivery.
			if (!data.test && (await hasVisibleAppClient())) {
				return;
			}

			await self.registration.showNotification(data.title, options);
		})()
	);
});

self.addEventListener('notificationclick', (event: NotificationEvent) => {
	event.notification.close();

	// Redirect to the URL provided in the push notification data
	const notificationData = (event.notification.data ?? {}) as NotificationClickData;
	const urlToOpen = new URL(notificationData.url ?? '/', self.location.origin).href;

	event.waitUntil(
		(async () => {
			const windowClients = await self.clients.matchAll({
				type: 'window',
				includeUncontrolled: true
			});

			// Reuse an already-open window when possible to avoid duplicate tabs.
			// Prefer one already at the target URL, otherwise focus the first
			// window and navigate it there (e.g. a PWA window on another page).
			const exactMatch = windowClients.find((client) => client.url === urlToOpen);
			if (exactMatch) {
				await exactMatch.focus();
				return;
			}

			const existing = windowClients[0];
			if (existing) {
				await existing.focus();
				// `navigate` can reject (e.g. cross-origin) — fall back to staying put.
				await existing.navigate(urlToOpen).catch(() => undefined);
				return;
			}

			// No window open at all — open a fresh one.
			if (self.clients.openWindow) {
				await self.clients.openWindow(urlToOpen);
			}
		})()
	);
});
