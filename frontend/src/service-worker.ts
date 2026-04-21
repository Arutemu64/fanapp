// Disables access to DOM typings like `HTMLElement` which are not available
// inside a service worker and instantiates the correct globals
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

// Ensures that the `$service-worker` import has proper type definitions
/// <reference types="@sveltejs/kit" />

// Only necessary if you have an import from `$env/static/public`
/// <reference types="../.svelte-kit/ambient.d.ts" />

import { build, files, version } from '$service-worker';

// This gives `self` the correct types
const self = globalThis.self as unknown as ServiceWorkerGlobalScope;

interface PushNotificationPayload {
	title: string;
	body: string;
	url: string;
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

const ASSETS = [
	...build, // the app itself
	...files // everything in `static`
];

self.addEventListener('install', (event) => {
	// Create a new cache and add all files to it
	async function addFilesToCache() {
		const cache = await caches.open(CACHE);
		await cache.addAll(ASSETS);
	}

	event.waitUntil(addFilesToCache());
});

self.addEventListener('activate', (event) => {
	// Remove previous cached data from disk
	async function deleteOldCaches() {
		for (const key of await caches.keys()) {
			if (key !== CACHE) await caches.delete(key);
		}
	}

	event.waitUntil(deleteOldCaches());
});

self.addEventListener('fetch', (event) => {
	// ignore POST requests etc
	if (event.request.method !== 'GET') return;

	// Skip EventSource requests
	if (event.request.headers.get('Accept') === 'text/event-stream') return;

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

		// for everything else, try the network first, but
		// fall back to the cache if we're offline
		try {
			const response = await fetch(event.request);

			// if we're offline, fetch can return a value that is not a Response
			// instead of throwing - and we can't pass this non-Response to respondWith
			if (!(response instanceof Response)) {
				throw new Error('invalid response from fetch');
			}

			if (response.status === 200) {
				cache.put(event.request, response.clone());
			}

			return response;
		} catch (err) {
			const response = await cache.match(event.request);

			if (response) {
				return response;
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
		title: 'FAN FAN',
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
		data: {
			url: data.url || '/'
		}
	};

	event.waitUntil(
		(async () => {
			// When the app is already visible, the user will see the in-app toast and bell update.
			// Skip the OS-level push notification to avoid duplicate alerts for the same message.
			if (await hasVisibleAppClient()) {
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
		self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
			// Check if there is already a window/tab open with the target URL
			for (const client of windowClients) {
				if (client.type !== 'window') {
					continue;
				}

				if (client.url === urlToOpen) {
					return client.focus();
				}
			}
			// If not, open a new window/tab
			if (self.clients.openWindow) {
				return self.clients.openWindow(urlToOpen);
			}
		})
	);
});
