// Disables access to DOM typings like `HTMLElement` which are not available
// inside a service worker and instantiates the correct globals
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

// Ensures that virtual imports (`$env/static/public`) have type definitions
/// <reference types="@sveltejs/kit" />
/// <reference types="../.svelte-kit/ambient.d.ts" />

import { PUBLIC_API_URL } from '$env/static/public';
import { clientsClaim } from 'workbox-core';
import {
	cleanupOutdatedCaches,
	createHandlerBoundToURL,
	precacheAndRoute,
	type PrecacheEntry
} from 'workbox-precaching';
import { NavigationRoute, registerRoute } from 'workbox-routing';
import { CacheFirst } from 'workbox-strategies';

// `self` with SW types, plus the manifest vite-pwa injects at build. It is
// absent in `vite dev` (injectManifest only runs on a production build); the
// guard below treats that absence as the signal to stay inert.
declare let self: ServiceWorkerGlobalScope & {
	__WB_MANIFEST: (string | PrecacheEntry)[] | undefined;
};

// The backend is deployed under a path on the *same* origin as the app
// (e.g. https://host/api), so an origin check can't tell API calls apart from
// the app shell. Derive the API's origin + base path from PUBLIC_API_URL and
// keep it network-only: the SW must never cache or replay user-specific,
// dynamic API data — the app's own IndexedDB layer owns offline caching, and a
// cached health/probe response would make us look online while the device is
// offline. Workbox never intercepts these (no route below matches the API path,
// and the navigation fallback denylists it), so they hit the network directly.
// PUBLIC_API_URL is relative by default (e.g. `/api`), so resolve it against
// this worker's own origin — `new URL` throws on a bare path without a base.
const API_URL = new URL(PUBLIC_API_URL, self.location.origin);
// Drop any trailing slash so the prefix match below is exact.
const API_BASE_PATH = API_URL.pathname.replace(/\/+$/, '');

// Matches the API base path and anything under it, anchored at the start.
const API_PATH_PATTERN = new RegExp(`^${API_BASE_PATH}(/|$)`);

// Caching only runs in a production build, where the manifest is injected. Its
// absence in dev means cache-first would be wrong anyway — that strategy assumes
// the immutable, versioned shell only a real build emits — so the worker stays
// inert. The push/notificationclick handlers below register either way, so push
// still works in dev.
const precacheManifest = self.__WB_MANIFEST;
if (precacheManifest) {
	// --- Precaching -----------------------------------------------------------
	// Precache the shell and serve it cache-first. Revisions are content hashes,
	// so a cache hit is never stale, and cleanupOutdatedCaches prunes entries left
	// by superseded revisions. The responsive image variants are kept out of the
	// manifest (vite.config globIgnores) and runtime-cached below instead.
	precacheAndRoute(precacheManifest);
	cleanupOutdatedCaches();

	// --- SPA navigation fallback ----------------------------------------------
	// Every route renders from the same client-built shell, precached above as
	// the adapter-static fallback (200.html). Serving it for navigations means
	// startup never depends on the origin being healthy — a reachable-but-broken
	// upstream (502/503/504) can't block the app from booting. API paths are
	// denylisted so a navigation-shaped API request still hits the network.
	registerRoute(
		new NavigationRoute(createHandlerBoundToURL('/200.html'), {
			denylist: [API_PATH_PATTERN]
		})
	);

	// --- Responsive image variants: runtime cache-first -----------------------
	// The AVIF/WebP/… variants <enhanced:img> emits are content-hashed and
	// immutable, so cache-first is safe (a hit is never stale) and they become
	// available offline after the first online view. Precached shell images
	// (icons) are already served by the precache route, so this only catches the
	// excluded hashed variants. API paths never have an `image` destination.
	registerRoute(
		({ url, request }) => url.origin === self.location.origin && request.destination === 'image',
		new CacheFirst({ cacheName: 'image-variants' })
	);

	// Take control of open pages after a controlled update (the in-app prompt
	// reloads them on `controllerchange`). We do NOT call skipWaiting here: a new
	// worker waits until the user accepts the prompt, which posts the `skipWaiting`
	// message handled below — never swapping assets mid-session.
	clientsClaim();
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

// The new worker waits by default so the user is never interrupted mid-session.
// The in-app "new version" prompt posts this message when the user accepts,
// which activates the waiting worker and triggers a reload.
self.addEventListener('message', (event) => {
	if (event.data === 'skipWaiting') {
		self.skipWaiting();
	}
});

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
		icon: '/icons/icon-192.png',
		// Android renders the badge as a monochrome silhouette from the alpha
		// channel alone, re-tinted with the system accent — so it must be a
		// transparent-background mark, not the opaque full-color app icon.
		badge: '/icons/badge-96.png',
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

			// Mirror the push onto the app-icon badge (Badging API, no-op where
			// unsupported). The payload carries no unread count, so set the
			// count-less "flag" badge; the in-app bell replaces it with the exact
			// number (or clears it) once the app opens.
			if ('setAppBadge' in self.navigator) {
				await self.navigator.setAppBadge().catch(() => undefined);
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
