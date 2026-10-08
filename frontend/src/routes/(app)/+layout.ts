import { countUnreadNotifications } from '#lib/api/generated/index.js';
import { createApiClient } from '#lib/api/index.js';
import { isReachable } from '#lib/services/reachability.js';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '#lib/utils/fetchTimeout.js';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = ({ fetch, depends, parent }) => {
	// The notification bell lives in the persistent app shell. Stream its unread
	// count rather than awaiting it: awaiting would gate the shell's first paint
	// behind `await parent()`'s /me and then another round-trip — a pure waterfall,
	// and `parent()` only earns its round-trip under SSR, which this client-only app
	// (ssr = false) never does. The badge seeds from this promise when it resolves
	// and the live SSE stream owns the count thereafter, so a slightly late seed is
	// invisible. See the SvelteKit performance guide on streaming to avoid load
	// waterfalls.
	depends('app:notifications');

	return { unreadCount: loadUnreadCount(fetch, parent) };
};

// Returns null when the badge can't be seeded (guest or offline); the SSE stream
// fills it in once connected. Kept as its own async so the load above returns the
// unresolved promise synchronously and never blocks first paint.
async function loadUnreadCount(
	fetch: typeof globalThis.fetch,
	parent: () => Promise<{ user: unknown }>
): Promise<number | null> {
	const { user } = await parent();

	// Guests never see the bell; when unreachable we can't load it. The shell has
	// already rendered either way, so skip the request and let SSE fill it later.
	if (!user || !isReachable()) {
		return null;
	}

	// The badge is non-critical: on error or timeout fall back to no seed, and the
	// live SSE stream refreshes it once the client reconnects.
	const { data, error } = await countUnreadNotifications({
		client: createApiClient(),
		fetch,
		signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
	});

	// Reachability is left to the health probe and the API interceptor: a slow
	// count on first paint is no evidence the backend is down, and flagging it
	// offline would send other pages (voting, the cached feeds) to their offline
	// states.
	if (error || !data) {
		return null;
	}
	return data.count;
}
