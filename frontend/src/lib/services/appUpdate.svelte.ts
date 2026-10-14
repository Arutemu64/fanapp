import { createContext } from 'svelte';

// How often to ask the browser to re-check the worker script while the app is
// open. Tuned for a live event where a fix may ship mid-session; the request is
// a cheap conditional GET that 304s when nothing changed.
const UPDATE_POLL_MS = 15 * 60 * 1000;

// How long apply() waits for the new worker to take control before loading the
// page anyway. A worker that went redundant, or a lost `skipWaiting` message,
// would otherwise leave a cancelled navigation with nothing behind it.
const ACTIVATION_TIMEOUT_MS = 3000;

/**
 * Tracks a newer build waiting in the service worker and applies it.
 *
 * A waiting worker is never activated behind the user's back mid-screen (that
 * could swap assets under them). It is applied when they tap the Profile hub's
 * update row, or at the next page change: the root layout's beforeNavigate
 * turns that link tap into a full load, the SvelteKit-documented way to move a
 * long-lived session onto a new deploy
 * (https://svelte.dev/docs/kit/configuration#version).
 */
class AppUpdateService {
	#waitingWorker = $state<ServiceWorker | null>(null);
	// Held so we can poll for new builds ourselves (see #check). The browser
	// checks the worker script only on navigations and registration, so without
	// this an installed PWA kept open all event day would not notice a hot-fix
	// deploy until a manual reload.
	#registration: ServiceWorkerRegistration | null = null;
	#targetUrl: string | null = null;
	#applying = false;
	#loading = false;

	get available() {
		return this.#waitingWorker !== null;
	}

	/** Start watching for updates. Returns the teardown. */
	start(): () => void {
		if (!('serviceWorker' in navigator)) return () => undefined;

		// Whether a worker already controls this page at startup. On a first-ever
		// visit there is no controller: the SW installs, activates, and calls
		// `clients.claim()`, which fires `controllerchange` even though nothing was
		// updated. Without this guard that initial claim would trigger a needless
		// full reload right after first paint. A genuine update always has a prior
		// controller, so gating the reload on this keeps the update flow working.
		const hadController = !!navigator.serviceWorker.controller;

		// `ready` (unlike getRegistration()) waits until the registration has an
		// active worker. On a first-ever visit registration may still be in flight
		// when this runs — getRegistration() would resolve `undefined` and silently
		// disable update polling for the whole session.
		void navigator.serviceWorker.ready.then((reg) => {
			this.#registration = reg;

			// A build may already be waiting from a previous visit.
			this.#adoptWaiting(reg);

			// Or one may already be installing — e.g. the browser's own on-navigation
			// update check started it before we got here. Its `updatefound` has
			// already fired, so the listener below would miss it and `reg.waiting` is
			// still null; watch it directly or the update never surfaces (an
			// intermittent miss depending on install timing).
			if (reg.installing) {
				this.#watchInstalling(reg, reg.installing);
			}

			// Or one finishes installing while the app is open.
			reg.addEventListener('updatefound', () => {
				if (reg.installing) {
					this.#watchInstalling(reg, reg.installing);
				}
			});

			// Re-check immediately in case a deploy landed while the app was closed,
			// then keep polling for the rest of the session.
			this.#check();
		});

		// Fires in every open tab once the new worker takes over — also in tabs that
		// never called apply(), which reload too rather than keep running old code
		// against the new worker's cache.
		const onControllerChange = () => {
			if (!hadController) return;
			this.#load();
		};
		navigator.serviceWorker.addEventListener('controllerchange', onControllerChange);

		// Re-check on foreground so reopening the installed PWA picks up a deploy
		// that landed while it was backgrounded, without waiting for the poll.
		document.addEventListener('visibilitychange', this.#check);
		const pollId = setInterval(this.#check, UPDATE_POLL_MS);

		return () => {
			navigator.serviceWorker.removeEventListener('controllerchange', onControllerChange);
			document.removeEventListener('visibilitychange', this.#check);
			clearInterval(pollId);
		};
	}

	/**
	 * Activate the waiting build, then load `targetUrl` (a navigation that was
	 * cancelled to make room for the update) or reload the current page.
	 */
	apply(targetUrl?: string) {
		if (!this.#waitingWorker || this.#applying) return;
		this.#applying = true;
		this.#targetUrl = targetUrl ?? null;
		this.#waitingWorker.postMessage('skipWaiting');
		setTimeout(() => this.#load(), ACTIVATION_TIMEOUT_MS);
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

	// Watch an installing worker and adopt it once it reaches `installed`. The
	// controller check tells an update (something to replace) from the first-ever
	// install (nothing to replace).
	#watchInstalling(reg: ServiceWorkerRegistration, worker: ServiceWorker) {
		worker.addEventListener('statechange', () => {
			if (worker.state === 'installed' && navigator.serviceWorker.controller) {
				this.#adoptWaiting(reg);
			}
		});
	}

	// Ask the browser to re-fetch the worker script; if it changed, the
	// updatefound/statechange flow above picks it up. Errors (offline) are
	// ignored — the next check retries. Arrow function so it can be a listener.
	#check = () => {
		if (document.visibilityState !== 'visible') return;
		// Skip while offline (nothing to fetch) or while an install is already in
		// flight — re-checking then just races our own update flow. navigator.onLine
		// is trusted only as a negative here, matching the reachability layer.
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
