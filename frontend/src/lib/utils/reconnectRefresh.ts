import { invalidateAll } from '$app/navigation';

/**
 * Coalesced catch-up refetch after connectivity recovers.
 *
 * Live SSE events only carry server-side *changes*, so any recovery — the SSE
 * stream re-establishing after a silent drop, the offline→online edge, or a
 * backgrounded tab foregrounding — must refetch to catch whatever moved while we
 * were disconnected. A single recovery routinely trips more than one of those
 * paths at once (network returns → the `online` edge fires *and* the stream
 * re-dials and completes its handshake), so the debounce is module-global rather
 * than per-service: it collapses that burst into one `invalidateAll`, and it also
 * stops a flapping connection from triggering a reload storm.
 *
 * The timestamp is deliberately module-scoped — it's a shared rate-limit clock,
 * not user- or session-scoped state, so it never needs resetting across
 * login/logout (mirrors the module-global reachability state it coordinates with).
 */
const REFRESH_DEBOUNCE_MS = 3000;

let lastRefresh = 0;

export function requestReconnectRefresh(): void {
	const now = Date.now();
	if (now - lastRefresh < REFRESH_DEBOUNCE_MS) return;
	lastRefresh = now;
	void invalidateAll();
}
