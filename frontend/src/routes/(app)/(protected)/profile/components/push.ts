// Web Push helpers.

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
