import { invalidateAll } from '$app/navigation';
import { classifyReachabilityChange } from '$lib/utils/reachabilityTransition';
import { createContext } from 'svelte';

import { isReachable, markReachable, onReachableChange, probeReachability } from './reachability';

// While offline, poll for recovery so the banner clears on its own. We don't
// poll while online — load outcomes, the SSE stream, and the `online` event
// already keep the state fresh, so there's no need to spend battery/data.
// The delay backs off (3s → 30s) the longer we stay offline to save battery on
// a long outage, while still reacting quickly once a real outage ends.
const RECOVERY_POLL_MIN_MS = 3000;
const RECOVERY_POLL_MAX_MS = 30000;

// Ignore repeat reconnects within this window so a flapping connection doesn't
// trigger a storm of full `invalidateAll` reloads.
const RECONNECT_REFRESH_DEBOUNCE_MS = 3000;

// A failed probe while the device still reports online is treated as a possibly
// transient blip (radio waking after the app is foregrounded, a brief NAT drop)
// rather than an outage: we keep re-probing for this long before committing to
// the "Нет связи с сервером" banner. During the window the app stays "online",
// so the SSE client's own honest "Восстанавливаем связь…" strip is what shows —
// never a premature offline error. Any probe that succeeds ends the window at
// once. See classifyReachabilityChange and docs — this is the transient-fault
// "let it self-correct before alarming" rule applied to reachability.
const OFFLINE_CONFIRM_WINDOW_MS = 5000;
// Gap between confirm re-probes. Kept short so a genuine recovery is noticed
// almost as soon as the network returns; each probe carries its own 3s timeout.
const OFFLINE_CONFIRM_PROBE_GAP_MS = 500;

function deviceOnlineNow(): boolean {
	// SSR / non-browser: assume online, matching reachability.ts.
	return typeof navigator === 'undefined' ? true : navigator.onLine;
}

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
	#unsubscribeReachable: (() => void) | null = null;
	// Confirm-window bookkeeping (see OFFLINE_CONFIRM_WINDOW_MS). #confirming is
	// true for the whole window, including while a re-probe is in flight and the
	// timer is momentarily null.
	#confirming = false;
	#confirmDeadline = 0;
	#confirmId: ReturnType<typeof setTimeout> | null = null;

	constructor() {
		this.#unsubscribeReachable = onReachableChange(() => {
			const reachable = isReachable();

			// Any reachable signal ends a running confirm window — including one that
			// classifies as 'noop' below (a success while we never left "online",
			// e.g. the SSE handshake reporting the backend reachable). Without this
			// the window would keep probing until its own next tick noticed.
			if (reachable && this.#confirming) this.#cancelConfirm();

			const transition = classifyReachabilityChange({
				wasOnline: this.#online,
				probeReachable: reachable,
				deviceOnline: deviceOnlineNow()
			});

			switch (transition) {
				case 'go-online':
					this.#cancelConfirm();
					this.#commit(true);
					return;
				case 'go-offline':
					this.#cancelConfirm();
					this.#commit(false);
					return;
				case 'confirm':
					// Might be a transient blip; verify before showing the offline
					// banner. A re-entrant "still offline" notification while a window
					// is already running is ignored — the window's own loop drives it.
					if (!this.#confirming) this.#startConfirm();
					return;
				case 'noop':
					return;
			}
		});

		// The `offline` event firing is a trustworthy negative; `online` only means
		// an interface appeared, so verify it with a probe.
		window.addEventListener('offline', this.#handleOffline);
		window.addEventListener('online', this.#handleOnline);
		document.addEventListener('visibilitychange', this.#handleVisibilityChange);

		// Initial check, then poll only if it turns out we're offline.
		void probeReachability();
		this.#syncPolling();
	}

	// Apply a confirmed connectivity state and, on a real offline→online edge,
	// refresh stale pages. Live SSE events only cover data that *changed*
	// server-side; the reload catches the rest. Debounced so a flapping
	// connection can't trigger reload storms.
	#commit(online: boolean) {
		const wasOnline = this.#online;
		this.#online = online;
		this.#syncPolling();

		if (!wasOnline && online) {
			const now = Date.now();
			if (now - this.#lastReconnectRefresh > RECONNECT_REFRESH_DEBOUNCE_MS) {
				this.#lastReconnectRefresh = now;
				void invalidateAll();
			}
		}
	}

	// Keep re-probing for OFFLINE_CONFIRM_WINDOW_MS before trusting a probe
	// failure as an outage. A probe that succeeds mid-window flips reachability
	// back, which routes through the 'go-online' branch above and cancels this.
	#startConfirm() {
		this.#confirming = true;
		this.#confirmDeadline = Date.now() + OFFLINE_CONFIRM_WINDOW_MS;
		this.#scheduleConfirmProbe();
	}

	#scheduleConfirmProbe() {
		this.#confirmId = setTimeout(() => {
			this.#confirmId = null;
			void (async () => {
				const reachable = await probeReachability();
				// The blip cleared — end the window and stay online. We never left
				// the "online" state during the window, so there is nothing to
				// commit or refresh here; just stop probing.
				if (reachable) {
					this.#cancelConfirm();
					return;
				}
				// A cancel (a trustworthy `offline` event, or teardown) also ends it.
				if (!this.#confirming) return;

				if (Date.now() >= this.#confirmDeadline) {
					this.#confirming = false;
					this.#commit(false);
					return;
				}
				this.#scheduleConfirmProbe();
			})();
		}, OFFLINE_CONFIRM_PROBE_GAP_MS);
	}

	#cancelConfirm() {
		this.#confirming = false;
		if (this.#confirmId) {
			clearTimeout(this.#confirmId);
			this.#confirmId = null;
		}
	}

	// Arrow functions so they keep `this` and stay removable by reference.
	#handleOffline = () => {
		// Trustworthy negative: the device has no network. Abandon any confirm
		// window and go offline at once so "Нет интернета" shows without delay.
		// markReachable may not notify (reachability could already be false from a
		// failed confirm probe), so commit explicitly rather than via the listener.
		this.#cancelConfirm();
		markReachable(false);
		this.#commit(false);
	};
	#handleOnline = () => void probeReachability();
	#handleVisibilityChange = () => {
		if (document.visibilityState === 'visible') void probeReachability();
	};

	/**
	 * Remove the global listeners and stop the recovery poll. The root layout
	 * lives for the app's lifetime in production, but dev HMR re-creates it —
	 * without this each cycle would stack another set of listeners (same reason
	 * EventsClient has destroy()).
	 */
	destroy() {
		this.#unsubscribeReachable?.();
		this.#unsubscribeReachable = null;
		this.#cancelConfirm();
		window.removeEventListener('offline', this.#handleOffline);
		window.removeEventListener('online', this.#handleOnline);
		document.removeEventListener('visibilitychange', this.#handleVisibilityChange);
		if (this.#pollId) {
			clearTimeout(this.#pollId);
			this.#pollId = null;
		}
	}

	// Start the recovery poll while offline; stop it once we're back.
	#syncPolling() {
		const shouldPoll = !this.#online;
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
				if (!this.#online) {
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
