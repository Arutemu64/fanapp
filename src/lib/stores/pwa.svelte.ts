import { getContext, setContext } from 'svelte';
import { browser } from '$app/environment';

export class PwaService {
    #deferredPrompt = $state<any>(null);
    #isInstalled = $state(false);
    #canInstall = $derived(this.#deferredPrompt !== null);
    #isIOS = $state(false);

    constructor() {
        if (browser) {
            this.#isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream;

            // Check if already installed
            if (window.matchMedia('(display-mode: standalone)').matches || (navigator as any).standalone) {
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
