import type { PWAInstallElement } from '@khmyznikov/pwa-install';

import { defineStore } from 'pinia';
import { readonly, ref } from 'vue';

const ELEMENT_TAG = 'pwa-install';

/**
 * Wraps the <pwa-install> web component (@khmyznikov/pwa-install).
 *
 * The library renders its own localized install dialog and handles every
 * platform (Chromium Web Install / `beforeinstallprompt`, iOS Safari "Add to
 * Home Screen", Apple desktop, menu instructions for Firefox and other Android
 * browsers, "open in a real browser" for in-app WebViews like Telegram or VK),
 * so this store only mirrors the element's state into Vue reactivity and
 * exposes a single entry point to open the dialog.
 */
export const usePwaStore = defineStore('pwa', () => {
	let element: PWAInstallElement | null = null;
	const canInstall = ref(false);
	const isApplePlatform = ref(false);
	const isAppleMobilePlatform = ref(false);

	// Standalone (installed) detection that does not depend on the element.
	function detectStandalone() {
		return (
			window.matchMedia('(display-mode: standalone)').matches ||
			(navigator as { standalone?: boolean }).standalone === true
		);
	}

	// Detect standalone mode synchronously — reliable and race-free, unlike the
	// element's `isUnderStandaloneMode`, which is set during its async init.
	const isInstalled = ref(detectStandalone());

	// Registers the <pwa-install> custom element. Imported dynamically so the
	// library lands in its own chunk instead of the initial bundle — the install
	// row is a small corner of the profile page.
	import('@khmyznikov/pwa-install').catch(() => {
		// Chunk failed to load; the install card just stays hidden.
	});

	// Named function so it can be passed straight to addEventListener/removeEventListener.
	function syncState() {
		const el = element;
		if (!el) return;

		// Combine our own detection with the element's signal (e.g. install-success).
		isInstalled.value = detectStandalone() || el.isUnderStandaloneMode;
		isApplePlatform.value = el.isAppleMobilePlatform || el.isAppleDesktopPlatform;
		isAppleMobilePlatform.value = el.isAppleMobilePlatform;
		// Offer installation wherever the library has something to show: Chromium's
		// prompt, its Android fallback (Firefox, Opera, in-app WebViews), or Apple
		// platforms, where it shows its own how-to instructions instead. Desktop
		// browsers that cannot install at all (Firefox, old Safari) stay hidden: a
		// forced dialog there would offer a button with nothing behind it.
		canInstall.value = !isInstalled.value && (el.isInstallAvailable || isApplePlatform.value);
	}

	/**
	 * Connect the mounted <pwa-install> element. Returns a cleanup function; call it
	 * when the element unmounts.
	 */
	function attach(target: PWAInstallElement) {
		element = target;

		target.addEventListener('pwa-install-available-event', syncState);
		target.addEventListener('pwa-install-success-event', syncState);
		target.addEventListener('pwa-user-choice-result-event', syncState);

		// The element upgrades asynchronously after the dynamic import resolves;
		// read its state once it is defined, then again on every lifecycle event.
		void customElements.whenDefined(ELEMENT_TAG).then(syncState);

		return () => {
			target.removeEventListener('pwa-install-available-event', syncState);
			target.removeEventListener('pwa-install-success-event', syncState);
			target.removeEventListener('pwa-user-choice-result-event', syncState);
			element = null;
		};
	}

	/**
	 * True on iPhone and iPad (the library counts a touch Mac UA as one, which is
	 * how iPadOS Safari reports itself). Web push there reaches only a Home Screen
	 * app (https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/);
	 * Safari on a Mac delivers it to an ordinary tab (https://webkit.org/?p=12945),
	 * so Apple desktop is deliberately not included.
	 */
	const pushRequiresInstall = readonly(isAppleMobilePlatform);

	/** Open the library's install dialog (forced, since we run it in manual mode). */
	function showInstallDialog() {
		element?.showDialog(true);
	}

	return {
		canInstall: readonly(canInstall),
		isInstalled: readonly(isInstalled),
		/**
		 * True on iOS/iPadOS and Apple desktop, where the library shows its own install
		 * instructions instead of a browser prompt, and where an installed app keeps its
		 * notification permission in the system settings.
		 */
		isApplePlatform: readonly(isApplePlatform),
		pushRequiresInstall,
		attach,
		showInstallDialog
	};
});
