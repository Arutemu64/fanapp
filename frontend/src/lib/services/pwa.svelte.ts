import { createContext } from 'svelte';
import { browser } from '$app/environment';
import type { PWAInstallElement } from '@khmyznikov/pwa-install';

const ELEMENT_TAG = 'pwa-install';

/**
 * Wraps the <pwa-install> web component (@khmyznikov/pwa-install).
 *
 * The library renders its own localized install dialog and handles every
 * platform (Chromium `beforeinstallprompt`, iOS Safari "Add to Home Screen",
 * Apple desktop, etc.), so this service only mirrors the element's state into
 * Svelte reactivity and exposes a single entry point to open the dialog.
 */
export class PwaService {
	#element: PWAInstallElement | null = null;
	#canInstall = $state(false);
	#isInstalled = $state(false);
	#isApplePlatform = $state(false);

	constructor() {
		if (browser) {
			// Registers the <pwa-install> custom element. Browser-only because the
			// module touches `window` at import time and would break SSR.
			import('@khmyznikov/pwa-install');
		}
	}

	/**
	 * Connect the mounted <pwa-install> element. Returns a cleanup function so it
	 * can be wired up with Svelte's `{@attach ...}` directive in the layout.
	 */
	attach(element: PWAInstallElement) {
		this.#element = element;

		element.addEventListener('pwa-install-available-event', this.#syncState);
		element.addEventListener('pwa-install-success-event', this.#syncState);
		element.addEventListener('pwa-user-choice-result-event', this.#syncState);

		// The element upgrades asynchronously after the dynamic import resolves;
		// read its state once it is defined, then again on every lifecycle event.
		if (browser) {
			customElements.whenDefined(ELEMENT_TAG).then(this.#syncState);
		}

		return () => {
			element.removeEventListener('pwa-install-available-event', this.#syncState);
			element.removeEventListener('pwa-install-success-event', this.#syncState);
			element.removeEventListener('pwa-user-choice-result-event', this.#syncState);
			this.#element = null;
		};
	}

	// Arrow function so it can be used directly as an event listener.
	#syncState = () => {
		const el = this.#element;
		if (!el) return;

		this.#isInstalled = el.isUnderStandaloneMode;
		this.#isApplePlatform = el.isAppleMobilePlatform || el.isAppleDesktopPlatform;
		// Offer installation when Chromium reports it is available, or on Apple
		// platforms where the library shows its own how-to instructions instead.
		this.#canInstall =
			!el.isUnderStandaloneMode && (el.isInstallAvailable || this.#isApplePlatform);
	};

	get canInstall() {
		return this.#canInstall;
	}

	get isInstalled() {
		return this.#isInstalled;
	}

	/** True on iOS/iPadOS and Apple desktop, where web push requires an installed PWA. */
	get isApplePlatform() {
		return this.#isApplePlatform;
	}

	/** Open the library's install dialog (forced, since we run it in manual mode). */
	showInstallDialog() {
		this.#element?.showDialog(true);
	}
}

const [getPwa, setPwa] = createContext<PwaService>();

export function setPwaService() {
	const service = new PwaService();
	setPwa(service);
	return service;
}

export function getPwaService() {
	return getPwa();
}
