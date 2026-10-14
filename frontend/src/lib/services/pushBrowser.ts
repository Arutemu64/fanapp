/**
 * The browser's Push API behind a small port, so `PushDevice` can be tested with a
 * fake and the capability check lives in exactly one place.
 */
export interface PushBrowser {
	/** Service worker, Push API and Notification API are all present. */
	isSupported: () => boolean;
	permission: () => NotificationPermission;
	requestPermission: () => Promise<NotificationPermission>;
	getSubscription: () => Promise<PushSubscription | null>;
	subscribe: (vapidKey: string) => Promise<PushSubscription>;
}

/**
 * Convert a base64url-encoded VAPID application server key into the
 * `Uint8Array` the Push API's `pushManager.subscribe` expects. VAPID keys are
 * distributed base64url (`-`/`_`, no padding), which `atob` cannot read, so pad
 * and translate back to standard base64 first.
 */
export function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
	const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
	const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');

	const rawData = window.atob(base64);
	const outputArray = new Uint8Array(rawData.length);

	for (let i = 0; i < rawData.length; ++i) {
		outputArray[i] = rawData.charCodeAt(i);
	}
	return outputArray;
}

// `getRegistration()` rather than `serviceWorker.ready` for every read: `ready`
// never resolves when no worker is registered (dev builds, a blocked
// registration), which would leave a caller waiting forever. With no registration
// there can be no subscription, so `undefined` already means "none".
async function getRegistration(): Promise<ServiceWorkerRegistration | undefined> {
	return navigator.serviceWorker.getRegistration();
}

export const browserPush: PushBrowser = {
	// No Push API means push is off here: iOS Safari only exposes it to a Home
	// Screen app (https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/),
	// and in-app browsers (Telegram, VK, Instagram, …) lack it outright. Android ones
	// report a plain Chrome UA, so the capability is detected rather than the user
	// agent sniffed.
	isSupported: () =>
		'serviceWorker' in navigator && 'PushManager' in window && typeof Notification !== 'undefined',

	permission: () => Notification.permission,

	requestPermission: () => Notification.requestPermission(),

	async getSubscription() {
		const registration = await getRegistration();
		return (await registration?.pushManager.getSubscription()) ?? null;
	},

	async subscribe(vapidKey) {
		const registration = await getRegistration();
		if (!registration) {
			throw new Error('No service worker registered');
		}
		// A registration can still be installing; `subscribe` needs an active worker.
		// `ready` is safe here because a registration exists, so it will resolve.
		await navigator.serviceWorker.ready;
		return registration.pushManager.subscribe({
			userVisibleOnly: true,
			applicationServerKey: urlBase64ToUint8Array(vapidKey)
		});
	}
};
