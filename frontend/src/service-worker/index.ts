import { dev, version } from '$app/env';
import { PUBLIC_API_URL } from '$app/env/public';
import { assets, immutable } from '$app/manifest';
import { self } from '$app/service-worker';
import { clientsClaim } from 'workbox-core';
import { ExpirationPlugin } from 'workbox-expiration';
import {
	cleanupOutdatedCaches,
	createHandlerBoundToURL,
	precacheAndRoute
} from 'workbox-precaching';
import { NavigationRoute, registerRoute } from 'workbox-routing';
import { CacheFirst } from 'workbox-strategies';

import { m } from '#lib/paraglide/messages.js';
import { buildPrecacheManifest } from '#lib/utils/precacheManifest.js';

const FALLBACK_PAGE = '200.html';

const API_URL = new URL(PUBLIC_API_URL, self.location.origin);
const API_BASE_PATH = API_URL.pathname.replace(/\/+$/, '');

const API_PATH_PATTERN = new RegExp(`^${API_BASE_PATH}(/|$)`);

interface StaticRoutingInstallEvent extends ExtendableEvent {
	addRoutes?: (rules: { condition: { urlPattern: string }; source: 'network' }) => Promise<void>;
}

if (!dev) {
	precacheAndRoute(
		buildPrecacheManifest({ immutable, assets, fallbackPage: FALLBACK_PAGE, version })
	);
	cleanupOutdatedCaches();

	self.addEventListener('install', (event: StaticRoutingInstallEvent) => {
		if (!event.addRoutes) {
			return;
		}
		event.waitUntil(
			event
				.addRoutes({
					condition: { urlPattern: `${API_URL.origin}${API_BASE_PATH}/*` },
					source: 'network'
				})
				.catch(() => undefined)
		);
	});

	registerRoute(
		new NavigationRoute(createHandlerBoundToURL(`/${FALLBACK_PAGE}`), {
			denylist: [API_PATH_PATTERN]
		})
	);

	registerRoute(
		({ url, request }) => url.origin === self.location.origin && request.destination === 'image',
		new CacheFirst({
			cacheName: 'image-variants',
			plugins: [
				new ExpirationPlugin({
					maxEntries: 60,
					maxAgeSeconds: 30 * 24 * 60 * 60,
					purgeOnQuotaError: true
				})
			]
		})
	);

	clientsClaim();
}

interface DeclarativePushMessage {
	notification: {
		title: string;
		body: string;
		navigate: string;
		tag?: string;
		renotify?: boolean;
		data?: {
			test?: boolean;
		};
	};
}

interface DeclarativePushEvent extends PushEvent {
	readonly notification?: Notification | null;
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

self.addEventListener('message', (event) => {
	if (event.data === 'skipWaiting') {
		void self.skipWaiting();
	}
});

function readPushMessage(data: PushMessageData | null): DeclarativePushMessage['notification'] {
	const fallback = { title: m.app_name(), body: m.push_default_body(), navigate: '/' };
	if (!data) {
		return fallback;
	}
	try {
		const message = data.json() as Partial<DeclarativePushMessage>;
		return { ...fallback, ...message.notification };
	} catch {
		return { ...fallback, body: data.text() };
	}
}

async function flagAppBadge() {
	if ('setAppBadge' in self.navigator) {
		await self.navigator.setAppBadge().catch(() => undefined);
	}
}

self.addEventListener('push', (event: DeclarativePushEvent) => {
	if (event.notification) {
		event.waitUntil(flagAppBadge());
		return;
	}

	const notification = readPushMessage(event.data);
	const options = {
		body: notification.body,
		icon: '/icons/icon-192.png',
		badge: '/icons/badge-96.png',
		tag: notification.tag,
		renotify: notification.renotify ?? false,
		data: {
			url: notification.navigate
		}
	};

	event.waitUntil(
		(async () => {
			if (!notification.data?.test && (await hasVisibleAppClient())) {
				return;
			}

			await flagAppBadge();
			await self.registration.showNotification(notification.title, options);
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

			const exactMatch = windowClients.find((client) => client.url === urlToOpen);
			if (exactMatch) {
				await exactMatch.focus();
				return;
			}

			const existing = windowClients[0];
			if (existing) {
				await existing.focus();
				await existing.navigate(urlToOpen).catch(() => undefined);
				return;
			}

			await self.clients.openWindow(urlToOpen);
		})()
	);
});
