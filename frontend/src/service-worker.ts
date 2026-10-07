// Disables access to DOM typings like `HTMLElement` which are not available
// inside a service worker and instantiates the correct globals
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

declare let self: ServiceWorkerGlobalScope;

// The worker exists for Web Push (and the Badging API it drives); it has no
// fetch handler, so every request goes straight to the network. With nothing to
// keep consistent across a page's requests, a new worker can take over at once —
// the waiting phase only guards a worker that serves assets
// (https://web.dev/articles/service-worker-lifecycle#skip_the_waiting_phase).
self.addEventListener('install', () => {
	void self.skipWaiting();
});

interface PushNotificationPayload {
	title: string;
	body: string;
	url: string;
	// Grouping key set by the backend: a topic ("schedule", "org") so a burst
	// collapses to the latest, or `notification.id` for ungrouped types (which
	// only collapses re-pushes of the same notification).
	tag?: string;
	// Set by the backend when `tag` is a topic: a replacement of the displayed
	// notification should still re-alert (sound/vibration) rather than update
	// silently. Requires a non-empty tag, which the topic path always provides.
	renotify?: boolean;
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
		// Re-alert on a same-tag replacement only for topic-grouped notifications;
		// the OS ignores it without a tag, and a unique-tag push has nothing to
		// replace anyway.
		renotify: data.renotify ?? false,
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
