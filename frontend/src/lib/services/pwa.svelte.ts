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
			// Detect standalone mode synchronously — reliable and race-free, unlike the
			// element's `isUnderStandaloneMode`, which is set during its async init.
			this.#isInstalled = this.#detectStandalone();

			// Registers the <pwa-install> custom element. Browser-only because the
			// module touches `window` at import time, so it must not load elsewhere.
			import('@khmyznikov/pwa-install').catch(() => {
				// Chunk failed to load; the install card just stays hidden.
			});
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

	// Standalone (installed) detection that does not depend on the element.
	#detectStandalone() {
		return (
			window.matchMedia('(display-mode: standalone)').matches ||
			(navigator as { standalone?: boolean }).standalone === true
		);
	}

	// Arrow function so it can be used directly as an event listener.
	#syncState = () => {
		const el = this.#element;
		if (!el) return;

		// Combine our own detection with the element's signal (e.g. install-success).
		this.#isInstalled = this.#detectStandalone() || el.isUnderStandaloneMode;
		this.#isApplePlatform = el.isAppleMobilePlatform || el.isAppleDesktopPlatform;
		// Offer installation when Chromium reports it is available, or on Apple
		// platforms where the library shows its own how-to instructions instead.
		this.#canInstall = !this.#isInstalled && (el.isInstallAvailable || this.#isApplePlatform);
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
