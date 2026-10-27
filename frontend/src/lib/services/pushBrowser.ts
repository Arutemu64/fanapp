export interface PushBrowser {
	isSupported: () => boolean;
	showsPushItself: () => boolean;
	permission: () => NotificationPermission;
	requestPermission: () => Promise<NotificationPermission>;
	getSubscription: () => Promise<PushSubscription | null>;
	subscribe: (vapidKey: string) => Promise<PushSubscription>;
}

function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
	const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
	const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');

	const rawData = window.atob(base64);
	const outputArray = new Uint8Array(rawData.length);

	for (let i = 0; i < rawData.length; ++i) {
		outputArray[i] = rawData.charCodeAt(i);
	}
	return outputArray;
}

async function getRegistration(): Promise<ServiceWorkerRegistration | undefined> {
	return navigator.serviceWorker.getRegistration();
}

const ACTIVATION_TIMEOUT_MS = 10_000;

export const browserPush: PushBrowser = {
	isSupported: () =>
		'serviceWorker' in navigator && 'PushManager' in window && typeof Notification !== 'undefined',

	showsPushItself: () => 'pushManager' in window,

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
		await Promise.race([
			navigator.serviceWorker.ready,
			new Promise<never>((_, reject) => {
				setTimeout(
					() => reject(new Error('Service worker did not activate')),
					ACTIVATION_TIMEOUT_MS
				);
			})
		]);
		return registration.pushManager.subscribe({
			userVisibleOnly: true,
			applicationServerKey: urlBase64ToUint8Array(vapidKey)
		});
	}
};
