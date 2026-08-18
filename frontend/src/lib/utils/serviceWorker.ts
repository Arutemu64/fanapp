import { dev } from '$app/environment';
import { base } from '$app/paths';

// We register the service worker ourselves instead of letting SvelteKit do it
// (svelte.config.js sets serviceWorker.register = false). SvelteKit's built-in
// registration leaves the register() promise's rejection unhandled, and some
// browsers reject it for reasons the app can do nothing about — storage
// partitioning in embedded/in-app browsers, private/incognito modes, or an
// enterprise policy that blocks workers. There the app simply degrades to
// online-only, which is expected; without a .catch() that rejection surfaces to
// Sentry as an uncaught "Error: Rejected". Mirrors SvelteKit's default: same
// script path and module/classic type, registered on load so it doesn't compete
// with first paint for bandwidth.
export function registerServiceWorker(): void {
	if (!('serviceWorker' in navigator)) return;

	const register = () => {
		navigator.serviceWorker
			.register(`${base}/service-worker.js`, { type: dev ? 'module' : 'classic' })
			.catch(() => undefined);
	};

	// `load` has already fired by the time the app hydrates on a warm/back-forward
	// navigation, so the listener would never run — register straight away then.
	if (document.readyState === 'complete') {
		register();
	} else {
		addEventListener('load', register, { once: true });
	}
}
