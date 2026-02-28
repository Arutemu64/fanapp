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

// Push Notifications Handling
sw.addEventListener('push', (event: any) => {
	let data = { title: 'FAN FAN', body: 'Новое уведомление', url: '/' };

	if (event.data) {
		try {
			// Try parsing as JSON first (expected format: { title, body, url })
			const json = event.data.json();
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
