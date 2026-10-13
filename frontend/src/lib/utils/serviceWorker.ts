// We register the service worker ourselves instead of letting vite-plugin-pwa
// inject its registration (`injectRegister: false` in vite.config.ts). A bare
// register() leaves the promise's rejection unhandled, and some browsers reject
// it for reasons the app can do nothing about — storage partitioning in
// embedded/in-app browsers, private/incognito modes, or an enterprise policy
// that blocks workers. There the app simply degrades to online-only, which is
// expected; without a .catch() that rejection surfaces to Sentry as an uncaught
// "Error: Rejected". Registered on load so it doesn't compete with first paint
// for bandwidth, and as a module worker — the plugin emits the worker as an ES
// module (`rollupFormat: 'es'`), so a browser without module service workers
// (Firefox < 147) rejects here and stays online-only.
const SCRIPT_URL = '/service-worker.js';

export function registerServiceWorker(): void {
	if (!('serviceWorker' in navigator)) return;

	const register = () => {
		navigator.serviceWorker.register(SCRIPT_URL, { type: 'module' }).catch((err) => {
			// Logged, not reported. Reporting brings back the noise this wrapper
			// exists to remove — the high-volume rejections are benign (see above)
			// — and the failures worth acting on (a 404 from a broken deploy, an
			// install-time throw) already fail far more loudly: the same deploy
			// 404s the app's own hashed assets, and a script bug is caught by the
			// build. console.debug keeps the real message to hand when someone is
			// actually looking (devtools, a deploy check).
			console.debug('Service worker registration failed:', err);
		});
	};

	// `load` has already fired by the time the app has booted on a warm/back-forward
	// navigation, so the listener would never run — register straight away then.
	if (document.readyState === 'complete') {
		register();
	} else {
		addEventListener('load', register, { once: true });
	}
}
