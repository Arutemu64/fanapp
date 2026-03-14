import { getContext, setContext } from 'svelte';
import { browser } from '$app/environment';

export class PwaService {
	#deferredPrompt = $state<any>(null);
	#isInstalled = $state(false);
	#canInstall = $derived(this.#deferredPrompt !== null);
	#isIOS = $state(false);
	#isAndroid = $state(false);
	#isSecureContext = $state(true);

	constructor() {
		if (browser) {
			const userAgent = navigator.userAgent;

			this.#isIOS = /iPad|iPhone|iPod/.test(userAgent) && !(window as any).MSStream;
			// Android browsers may still allow installation from the browser menu
			// even when `beforeinstallprompt` is not fired.
			this.#isAndroid = /Android/i.test(userAgent);
			this.#isSecureContext = window.isSecureContext;

			// Check if already installed
			if (
				window.matchMedia('(display-mode: standalone)').matches ||
				(navigator as any).standalone
			) {
				this.#isInstalled = true;
			}

			window.addEventListener('beforeinstallprompt', (e) => {
				e.preventDefault();
				this.#deferredPrompt = e;
			});

			window.addEventListener('appinstalled', () => {
				this.#deferredPrompt = null;
				this.#isInstalled = true;
			});
		}
	}

	get deferredPrompt() {
		return this.#deferredPrompt;
	}

	get isInstalled() {
		return this.#isInstalled;
	}

	get canInstall() {
		return this.#canInstall;
	}

	get isIOS() {
		return this.#isIOS;
	}

	get isAndroid() {
		return this.#isAndroid;
	}

	get isSecureContext() {
		return this.#isSecureContext;
	}

	async install() {
		if (this.#deferredPrompt) {
			this.#deferredPrompt.prompt();
			const { outcome } = await this.#deferredPrompt.userChoice;
			if (outcome === 'accepted') {
				this.#deferredPrompt = null;
			}
		}
	}
}

const PWA_CONTEXT_KEY = Symbol('pwa');

export function setPwaService() {
	const service = new PwaService();
	return setContext(PWA_CONTEXT_KEY, service);
}

export function getPwaService() {
	return getContext<PwaService>(PWA_CONTEXT_KEY);
}
