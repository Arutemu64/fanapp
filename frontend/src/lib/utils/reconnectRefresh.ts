import type { QueryClient } from '@tanstack/svelte-query';

/**
 * Coalesced catch-up refetch after connectivity recovers.
 *
 * Live SSE events only carry server-side *changes*, so any recovery — the SSE
 * stream re-establishing after a silent drop, the offline→online edge, or a
 * backgrounded tab foregrounding — must refetch to catch whatever moved while we
 * were disconnected. A single recovery routinely trips more than one of those
 * paths at once (network returns → the `online` edge fires *and* the stream
 * re-dials and completes its handshake), so the debounce is module-global rather
 * than per-service: it collapses that burst into one invalidation, and it also
 * stops a flapping connection from triggering a refetch storm.
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
 * The timer state is deliberately module-scoped — a shared rate-limit clock, not
 * user- or session-scoped state, so it never needs resetting across login/logout.
 * The QueryClient is passed in per call rather than held here, precisely because
 * it *is* session-scoped.
 */
const REFRESH_DEBOUNCE_MS = 3000;

let lastRefresh = 0;
let trailingTimer: ReturnType<typeof setTimeout> | null = null;

function refreshNow(queryClient: QueryClient): void {
	lastRefresh = Date.now();
	// Default scope: only queries a mounted component is observing. A recovery
	// should catch up what the user is looking at, not refetch every route they
	// happen to have visited this session.
	void queryClient.invalidateQueries();
}

export function requestReconnectRefresh(queryClient: QueryClient): void {
	const sinceLast = Date.now() - lastRefresh;
	if (sinceLast >= REFRESH_DEBOUNCE_MS) {
		refreshNow(queryClient);
		return;
	}

	// Inside the window: a possibly-distinct recovery the leading refresh may not
	// have covered. One trailing refresh catches the latest state; further requests
	// in the same window fold into the timer already set.
	if (trailingTimer !== null) return;
	trailingTimer = setTimeout(() => {
		trailingTimer = null;
		refreshNow(queryClient);
	}, REFRESH_DEBOUNCE_MS - sinceLast);
}
