import type { PWAInstallElement } from '@khmyznikov/pwa-install';

import { createContext } from 'svelte';

const ELEMENT_TAG = 'pwa-install';

class PwaService {
	#element: PWAInstallElement | null = null;
	#canInstall = $state(false);
	#isInstalled = $state(false);
	#isApplePlatform = $state(false);
	#isAppleMobilePlatform = $state(false);

	constructor() {
		this.#isInstalled = this.#detectStandalone();

		import('@khmyznikov/pwa-install').catch(() => {});
	}

	attach(element: PWAInstallElement) {
		this.#element = element;

		element.addEventListener('pwa-install-available-event', this.#syncState);
		element.addEventListener('pwa-install-success-event', this.#syncState);
		element.addEventListener('pwa-user-choice-result-event', this.#syncState);

		void customElements.whenDefined(ELEMENT_TAG).then(this.#syncState);

		return () => {
			element.removeEventListener('pwa-install-available-event', this.#syncState);
			element.removeEventListener('pwa-install-success-event', this.#syncState);
			element.removeEventListener('pwa-user-choice-result-event', this.#syncState);
			this.#element = null;
		};
	}

	#detectStandalone() {
		return (
			window.matchMedia('(display-mode: standalone)').matches ||
			(navigator as { standalone?: boolean }).standalone === true
		);
	}

	readonly #syncState = () => {
		const el = this.#element;
		if (!el) return;

		this.#isInstalled = this.#detectStandalone() || el.isUnderStandaloneMode;
		this.#isApplePlatform = el.isAppleMobilePlatform || el.isAppleDesktopPlatform;
		this.#isAppleMobilePlatform = el.isAppleMobilePlatform;
		this.#canInstall = !this.#isInstalled && (el.isInstallAvailable || this.#isApplePlatform);
	};

	get canInstall() {
		return this.#canInstall;
	}

	get isInstalled() {
		return this.#isInstalled;
	}

	get isApplePlatform() {
		return this.#isApplePlatform;
	}

	get pushRequiresInstall() {
		return this.#isAppleMobilePlatform;
	}

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
