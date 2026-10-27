import { createContext } from 'svelte';

const UPDATE_POLL_MS = 15 * 60 * 1000;

const ACTIVATION_TIMEOUT_MS = 3000;

class AppUpdateService {
	#waitingWorker = $state<ServiceWorker | null>(null);
	#registration: ServiceWorkerRegistration | null = null;
	#targetUrl: string | null = null;
	#applying = false;
	#loading = false;

	get available() {
		return this.#waitingWorker !== null;
	}

	start(): () => void {
		if (!('serviceWorker' in navigator)) return () => undefined;

		const hadController = !!navigator.serviceWorker.controller;

		void navigator.serviceWorker.ready.then((reg) => {
			this.#registration = reg;

			this.#adoptWaiting(reg);

			if (reg.installing) {
				this.#watchInstalling(reg, reg.installing);
			}

			reg.addEventListener('updatefound', () => {
				if (reg.installing) {
					this.#watchInstalling(reg, reg.installing);
				}
			});

			this.#check();
		});

		const onControllerChange = () => {
			if (!hadController) return;
			this.#load();
		};
		navigator.serviceWorker.addEventListener('controllerchange', onControllerChange);

		document.addEventListener('visibilitychange', this.#check);
		const pollId = setInterval(this.#check, UPDATE_POLL_MS);

		return () => {
			navigator.serviceWorker.removeEventListener('controllerchange', onControllerChange);
			document.removeEventListener('visibilitychange', this.#check);
			clearInterval(pollId);
		};
	}

	apply(targetUrl?: string) {
		if (!this.#waitingWorker || this.#applying) return;
		this.#applying = true;
		this.#targetUrl = targetUrl ?? null;
		setTimeout(() => this.#load(), ACTIVATION_TIMEOUT_MS);
		this.#waitingWorker.postMessage('skipWaiting');
	}

	#load() {
		if (this.#loading) return;
		this.#loading = true;
		if (this.#targetUrl) {
			window.location.href = this.#targetUrl;
		} else {
			window.location.reload();
		}
	}

	#adoptWaiting(reg: ServiceWorkerRegistration) {
		if (reg.waiting) {
			this.#waitingWorker = reg.waiting;
		}
	}

	#watchInstalling(reg: ServiceWorkerRegistration, worker: ServiceWorker) {
		worker.addEventListener('statechange', () => {
			if (worker.state === 'installed' && navigator.serviceWorker.controller) {
				this.#adoptWaiting(reg);
			}
		});
	}

	readonly #check = () => {
		if (document.visibilityState !== 'visible') return;
		if (!navigator.onLine) return;
		if (this.#registration?.installing) return;
		this.#registration?.update().catch(() => undefined);
	};
}

const [getAppUpdate, setAppUpdate] = createContext<AppUpdateService>();

export function setAppUpdateService() {
	const service = new AppUpdateService();
	setAppUpdate(service);
	return service;
}

export function getAppUpdateService() {
	return getAppUpdate();
}
