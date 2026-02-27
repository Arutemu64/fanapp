// Disables access to DOM typings like `HTMLElement` which are not available
// inside a service worker and instantiates the correct globals
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

// Ensures that the `$service-worker` import has proper type definitions
/// <reference types="@sveltejs/kit" />

import { build, files, version } from '$service-worker';

const sw = globalThis.self as unknown as ServiceWorkerGlobalScope;

const CACHE = `cache-${version}`;

const ASSETS = [
	...build, // the app itself
	...files // everything in `static`
];

sw.addEventListener('install', (event: any) => {
	// Create a new cache and add all files to it
	async function addFilesToCache() {
		const cache = await caches.open(CACHE);
		await cache.addAll(ASSETS);
	}

	event.waitUntil(addFilesToCache());
});

sw.addEventListener('activate', (event: any) => {
	// Remove previous cached data from disk
	async function deleteOldCaches() {
		for (const key of await caches.keys()) {
			if (key !== CACHE) await caches.delete(key);
		}
	}

	event.waitUntil(deleteOldCaches());
});

sw.addEventListener('fetch', (event: any) => {
	// ignore POST requests etc
	if (event.request.method !== 'GET') return;

	// Ignore Server-Sent Events to prevent Service Worker interception errors
	if (event.request.headers.get('accept')?.includes('text/event-stream')) return;

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
sw.addEventListener('push', (event: any) => {
	let data = { title: 'Notification', body: 'Новое уведомление', url: '/' };
	try {
		if (event.data) {
			data = event.data.json();
		}
	} catch (e) {
		// Fallback if data is not JSON
		console.error('Error parsing push data', e);
		if (event.data) {
			data.body = event.data.text();
		}
	}

	const options = {
		body: data.body,
		icon: '/favicon.png', // Assuming there's a favicon.png in static
		badge: '/favicon.png',
		data: {
			url: data.url || '/'
		}
	};

	event.waitUntil(sw.registration.showNotification(data.title, options));
});

sw.addEventListener('notificationclick', (event: any) => {
	event.notification.close();

	// Redirect to the URL provided in the push notification data
	const urlToOpen = new URL(event.notification.data.url, sw.location.origin).href;

	event.waitUntil(
		sw.clients
			.matchAll({ type: 'window', includeUncontrolled: true })
			.then((windowClients: any) => {
				// Check if there is already a window/tab open with the target URL
				for (let i = 0; i < windowClients.length; i++) {
					const client = windowClients[i];
					if (client.url === urlToOpen && 'focus' in client) {
						return client.focus();
					}
				}
				// If not, open a new window/tab
				if (sw.clients.openWindow) {
					return sw.clients.openWindow(urlToOpen);
				}
			})
	);
});
