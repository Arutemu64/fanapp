import { getContext, setContext } from 'svelte';
import { browser } from '$app/environment';

interface BeforeInstallPromptEvent extends Event {
	prompt: () => Promise<void>;
	userChoice: Promise<{
		outcome: 'accepted' | 'dismissed';
		platform: string;
	}>;
}

interface NavigatorWithStandalone extends Navigator {
	standalone?: boolean;
}

interface WindowWithMSStream extends Window {
	MSStream?: unknown;
}

export class PwaService {
	#deferredPrompt = $state<BeforeInstallPromptEvent | null>(null);
	#isInstalled = $state(false);
	#canInstall = $derived(this.#deferredPrompt !== null);
	#isIOS = $state(false);
	#isAndroid = $state(false);
	#isSecureContext = $state(true);

	constructor() {
		if (browser) {
			const userAgent = navigator.userAgent;
			const browserWindow = window as WindowWithMSStream;
			const browserNavigator = navigator as NavigatorWithStandalone;

			this.#isIOS = /iPad|iPhone|iPod/.test(userAgent) && !browserWindow.MSStream;
			// Android browsers may still allow installation from the browser menu
			// even when `beforeinstallprompt` is not fired.
			this.#isAndroid = /Android/i.test(userAgent);
			this.#isSecureContext = window.isSecureContext;

			// Check if already installed
			if (
				window.matchMedia('(display-mode: standalone)').matches ||
				browserNavigator.standalone === true
			) {
				this.#isInstalled = true;
			}

			window.addEventListener('beforeinstallprompt', (event: Event) => {
				const promptEvent = event as BeforeInstallPromptEvent;
				promptEvent.preventDefault();
				this.#deferredPrompt = promptEvent;
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
