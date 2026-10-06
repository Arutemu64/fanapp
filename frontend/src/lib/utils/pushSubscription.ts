/** Whether this device receives push, for an at-a-glance status line. */
export type DevicePushState = 'on' | 'off' | 'unknown';

/**
 * Read this device's push state from the browser alone — no network, so it works
 * offline and costs nothing on the profile hub. It can disagree with the server
 * in one rare case (the server dropped a subscription the browser still holds);
 * the notifications page does the server round-trip and is the source of truth.
 *
 * `getRegistration()` rather than `serviceWorker.ready`: `ready` never resolves
 * when no worker is registered (dev builds, a blocked registration), and with no
 * registration there can be no subscription, so `undefined` already means "off".
 */
export async function getDevicePushState(): Promise<DevicePushState> {
	if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
		return 'unknown';
	}
	if (typeof Notification === 'undefined') {
		return 'unknown';
	}
	if (Notification.permission !== 'granted') {
		return 'off';
	}

	try {
		const registration = await navigator.serviceWorker.getRegistration();
		const subscription = await registration?.pushManager.getSubscription();
		return subscription ? 'on' : 'off';
	} catch {
		// A status line is not worth an error: show nothing rather than a guess.
		return 'unknown';
	}
}
