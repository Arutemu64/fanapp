import { flushPendingLogout } from '#lib/utils/pendingLogout.js';
import { requestReconnectRefresh } from '#lib/utils/reconnectRefresh.js';

import { isReachable, markReachable, onReachableChange, probeReachability } from './reachability';

// While unreachable, poll for recovery so the offline banner clears on its own.
// We don't poll while reachable — API responses, the SSE stream and the browser
// events below already keep the state fresh, so there's no battery/data to spend.
// The delay backs off the longer we stay offline to save battery on a long
// outage, while still reacting quickly once a short one ends.
const RECOVERY_POLL_MIN_MS = 3000;
const RECOVERY_POLL_MAX_MS = 30000;

/**
 * Keep reachability (`reachability.ts`) current for the app's lifetime and act on
 * recovery. Call once from the root layout; returns the teardown, which matters
 * for dev HMR — without it each cycle would stack another poll and listener set.
 *
 * On the offline→online edge it fires an offline logout's queued revoke and
 * refreshes the pages, which may be showing cached copies. Live SSE events only
 * cover data that *changed* server-side, so the refresh catches the rest; it is
 * debounced together with the SSE reconnect's own catch-up.
 */
export function startReachabilityMonitor(): () => void {
	let pollTimerId: ReturnType<typeof setTimeout> | null = null;
	let pollDelayMs = RECOVERY_POLL_MIN_MS;

	function schedulePoll() {
		pollTimerId = setTimeout(() => {
			void (async () => {
				await probeReachability();
				// Recovery stops the loop through the edge handler below; this guard
				// also covers a teardown that ran while the probe was in flight.
				if (pollTimerId === null || isReachable()) return;
				pollDelayMs = Math.min(pollDelayMs * 2, RECOVERY_POLL_MAX_MS);
				schedulePoll();
			})();
		}, pollDelayMs);
	}

	function startPolling() {
		if (pollTimerId !== null) return;
		pollDelayMs = RECOVERY_POLL_MIN_MS;
		schedulePoll();
	}

	function stopPolling() {
		if (pollTimerId === null) return;
		clearTimeout(pollTimerId);
		pollTimerId = null;
	}

	// Listeners only fire on a change, so a reachable verdict here is always the
	// offline→online edge.
	const unsubscribe = onReachableChange(() => {
		if (!isReachable()) {
			startPolling();
			return;
		}

		stopPolling();
		// Revoke a session the user logged out of while offline, before the refresh
		// below re-runs /me — the pending flag keeps identity logged-out until this
		// clears, so there's no "logged back in" flicker in between.
		void flushPendingLogout();
		requestReconnectRefresh();
	});

	// The `offline` event is a trustworthy negative; `online` only means an
	// interface appeared, so verify it with a probe. Foregrounding is when a
	// mobile connection most often changed while we weren't looking.
	const handleOffline = () => markReachable(false);
	const handleOnline = () => void probeReachability();
	const handleVisibilityChange = () => {
		if (document.visibilityState === 'visible') void probeReachability();
	};
	window.addEventListener('offline', handleOffline);
	window.addEventListener('online', handleOnline);
	document.addEventListener('visibilitychange', handleVisibilityChange);

	// A root `load` may already have found us offline before this started, which
	// is no longer a change the listener above would see.
	if (!isReachable()) startPolling();
	void probeReachability();

	// Fire any logout queued while offline. A boot that is already online never
	// crosses the edge above, so flush here too; offline this is a no-op and the
	// edge picks it up on reconnect.
	void flushPendingLogout();

	return () => {
		unsubscribe();
		stopPolling();
		window.removeEventListener('offline', handleOffline);
		window.removeEventListener('online', handleOnline);
		document.removeEventListener('visibilitychange', handleVisibilityChange);
	};
}
