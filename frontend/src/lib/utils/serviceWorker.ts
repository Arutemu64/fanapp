import type { AssetPath } from '$app/types';

import { asset } from '$app/paths';

const SCRIPT_URL = asset('service-worker.js' as AssetPath);

export function registerServiceWorker(): void {
	if (!('serviceWorker' in navigator)) return;

	const register = () => {
		navigator.serviceWorker.register(SCRIPT_URL, { type: 'module' }).catch((err: unknown) => {
			// eslint-disable-next-line no-console -- debug-level on purpose, see above
			console.debug('Service worker registration failed:', err);
		});
	};

	if (document.readyState === 'complete') {
		register();
	} else {
		addEventListener('load', register, { once: true });
	}
}
