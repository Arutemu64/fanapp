/**
 * Coalesced catch-up refetch after connectivity recovers.
 *
 * Live SSE events only carry server-side *changes*, so any recovery — the SSE
 * stream re-establishing after a silent drop, the offline→online edge, or a
 * backgrounded tab foregrounding — must refetch to catch whatever moved while we
 * were disconnected. A single recovery routinely trips more than one of those
 * paths at once (network returns → the `online` edge fires *and* the stream
 * re-dials and completes its handshake), so the debounce is module-global rather
 * than per-service: it collapses that burst into one refresh, and it also stops a
 * flapping connection from triggering a reload storm.
 *
 * Leading *and* trailing: the first request in an idle period refreshes at once
 * (fast feedback for the common single-recovery case), and any request that
 * arrives while the window is still open schedules exactly one trailing refresh
 * at the window's end. The trailing edge matters because two *distinct* recovery
 * cycles can complete within one window — a leading-only debounce would discard
 * the second and leave its missed changes stale until an unrelated refresh. The
 * single trailing timer caps a flapping connection at one refresh per window, so
 * catching the latest state never costs a storm.
 *
 * The state is deliberately module-scoped — a shared rate-limit clock, not user-
 * or session-scoped state, so it never needs resetting across login/logout
 * (mirrors the module-global reachability state it coordinates with).
 */
const REFRESH_DEBOUNCE_MS = 3000;

let lastRefresh = 0;
let trailingTimer: ReturnType<typeof setTimeout> | null = null;

// Set by the root layout, which owns the QueryClient. This module must not hold
// the client itself — it caches the viewer's data, and a module singleton would
// outlive login/logout. Only the wiring lives here, alongside the debounce clock.
let refresh: (() => void) | null = null;

/**
 * Register what a recovery should refetch. The root layout passes a closure over
 * the QueryClient it created, invalidating every query so active ones refetch and
 * the rest are marked stale for their next read.
 */
export function onReconnectRefresh(handler: () => void): void {
	refresh = handler;
}

function refreshNow(): void {
	lastRefresh = Date.now();
	refresh?.();
}

export function requestReconnectRefresh(): void {
	const sinceLast = Date.now() - lastRefresh;
	if (sinceLast >= REFRESH_DEBOUNCE_MS) {
		refreshNow();
		return;
	}

	// Inside the window: a possibly-distinct recovery the leading refresh may not
	// have covered. One trailing refresh catches the latest state; further requests
	// in the same window fold into the timer already set.
	if (trailingTimer !== null) return;
	trailingTimer = setTimeout(() => {
		trailingTimer = null;
		refreshNow();
	}, REFRESH_DEBOUNCE_MS - sinceLast);
}
