import { browser } from '$app/environment';
import { invalidateAll } from '$app/navigation';
import { createContext } from 'svelte';

import { isReachable, markReachable, onReachableChange, probeReachability } from './reachability';

// While offline, poll for recovery so the banner clears on its own. We don't
// poll while online — load outcomes, the SSE stream, and the `online` event
// already keep the state fresh, so there's no need to spend battery/data.
// The delay backs off (5s → 30s) the longer we stay offline to save battery on
// a long outage, while still reacting quickly to a brief blip.
const RECOVERY_POLL_MIN_MS = 5000;
const RECOVERY_POLL_MAX_MS = 30000;

// Ignore repeat reconnects within this window so a flapping connection doesn't
// trigger a storm of full `invalidateAll` reloads.
const RECONNECT_REFRESH_DEBOUNCE_MS = 3000;

/**
 * Reactive view over server reachability (see `reachability.ts`), driving the
 * offline banner. Re-probes on the events that usually coincide with a
 * connectivity change, and polls only while offline to detect recovery.
 *
 * This reflects whether the *backend* is reachable, not `navigator.onLine` —
 * so it stays correct on a dead VPN / captive network that lies about being
 * online. Distinct from the SSE `EventsClient` reconnect state.
 */
export class OfflineService {
	#online = $state(isReachable());
	#pollId: ReturnType<typeof setTimeout> | null = null;
	#pollDelay = RECOVERY_POLL_MIN_MS;
	#lastReconnectRefresh = 0;

	constructor() {
		if (!browser) return;

		onReachableChange(() => {
			const wasOnline = this.#online;
			this.#online = isReachable();
			this.#syncPolling();

			// Recovered from offline: re-run every load so pages still showing the
			// last cached copy refresh and drop their stale notices. Live SSE events
			// only cover data that *changed* server-side; this catches the rest.
			// Debounced so a flapping connection can't trigger reload storms.
			if (!wasOnline && this.#online) {
				const now = Date.now();
				if (now - this.#lastReconnectRefresh > RECONNECT_REFRESH_DEBOUNCE_MS) {
					this.#lastReconnectRefresh = now;
					void invalidateAll();
				}
			}
		});

		// The `offline` event firing is a trustworthy negative; `online` only means
		// an interface appeared, so verify it with a probe.
		window.addEventListener('offline', () => markReachable(false));
		window.addEventListener('online', () => void probeReachability());
		document.addEventListener('visibilitychange', () => {
			if (document.visibilityState === 'visible') void probeReachability();
		});

		// Initial check, then poll only if it turns out we're offline.
		void probeReachability();
		this.#syncPolling();
	}

	// Start the recovery poll while offline; stop it once we're back.
	#syncPolling() {
		const shouldPoll = browser && !this.#online;
		if (shouldPoll && !this.#pollId) {
			this.#pollDelay = RECOVERY_POLL_MIN_MS;
			this.#scheduleNextPoll();
		} else if (!shouldPoll && this.#pollId) {
			clearTimeout(this.#pollId);
			this.#pollId = null;
			this.#pollDelay = RECOVERY_POLL_MIN_MS;
		}
	}

	// Probe once, then (if still offline) reschedule with a longer delay. A
	// recovering probe flips #online via onReachableChange, which clears the
	// timer through #syncPolling, so the `!this.#online` guard stops the loop.
	#scheduleNextPoll() {
		this.#pollId = setTimeout(() => {
			// setTimeout wants a void callback; run the async probe fire-and-forget.
			void (async () => {
				await probeReachability();
				if (browser && !this.#online) {
					this.#pollDelay = Math.min(this.#pollDelay * 2, RECOVERY_POLL_MAX_MS);
					this.#scheduleNextPoll();
				}
			})();
		}, this.#pollDelay);
	}

	/** True when the backend is reachable. */
	get isOnline(): boolean {
		return this.#online;
	}
}

const [getOffline, setOffline] = createContext<OfflineService>();

/** Create and set the OfflineService in context (call in the root layout). */
export function setOfflineService() {
	const service = new OfflineService();
	setOffline(service);
	return service;
}

export function getOfflineService() {
	return getOffline();
}

/**
 * Whether a page should show the "showing cached/stale data" notice. True when
 * the loaded copy is cached (`stale`) or the device went offline since open —
 * in both cases what's on screen may be out of date until reconnect. Suppressed
 * on an offline cold miss (`offlineMiss`): there's no saved copy to caveat, so
 * the page's dedicated empty state explains the situation instead.
 */
export function shouldShowStaleNotice(opts: {
	offlineMiss: boolean;
	stale: boolean;
	isOnline: boolean;
}): boolean {
	return !opts.offlineMiss && (opts.stale || !opts.isOnline);
}
