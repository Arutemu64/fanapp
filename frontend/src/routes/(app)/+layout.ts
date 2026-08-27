import type { NotificationSeed } from '$lib/types/notifications';

import { createApiClient } from '$lib/api';
import { NOTIFICATION_PREVIEW_LIMIT } from '$lib/constants/notifications';
import { isReachable, markReachable } from '$lib/services/reachability';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = ({ fetch, depends, parent }) => {
	// The notification bell lives in the persistent app shell. Stream its preview
	// and unread count rather than awaiting them: awaiting gated the shell's first
	// paint behind `await parent()`'s /me and then two more round-trips — a pure
	// waterfall, and `parent()` only earns its round-trip under SSR, which this
	// client-only app (ssr = false) never does. The bell seeds from this promise
	// when it resolves and the live SSE stream owns the count thereafter, so a
	// slightly late seed is invisible. See the SvelteKit performance guide on
	// streaming to avoid load waterfalls.
	depends('app:notifications');

	return { notifications: loadNotificationSeed(fetch, parent) };
};

// Returns null when the bell can't be seeded (guest or offline); the SSE stream
// fills it in once connected. Kept as its own async so the load above returns the
// unresolved promise synchronously and never blocks first paint.
async function loadNotificationSeed(
	fetch: typeof globalThis.fetch,
	parent: () => Promise<{ user: unknown }>
): Promise<NotificationSeed | null> {
	const { user } = await parent();

	// Guests never see the bell; when unreachable we can't load it. The shell has
	// already rendered either way, so skip the request and let SSE fill it later.
	if (!user || !isReachable()) {
		return null;
	}

	const client = createApiClient();

	// The bell is non-critical: on error/timeout (or offline) fall back to an empty
	// preview. The live SSE stream refreshes it once the client reconnects. The
	// preview feeds the dropdown list; the unread count is fetched separately
	// because the badge must reflect the true total, not the capped preview length
	// (a preview of 5 can hide dozens of unread items).
	//
	// The two requests fire in parallel but their failures stay independent: the
	// preview alone decides reachability (as it did before the count was added), and
	// a timed-out count must not discard a good preview or mark the API unreachable.
	const [previewResult, unreadResult] = await Promise.allSettled([
		client.GET('/notifications/', {
			fetch,
			params: { query: { limit: NOTIFICATION_PREVIEW_LIMIT } },
			signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
		}),
		client.GET('/notifications/unread-count', {
			fetch,
			signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
		})
	]);

	if (previewResult.status === 'rejected') {
		markReachable(false);
		return { preview: [], unreadCount: 0 };
	}
	markReachable(true);

	const preview = previewResult.value;
	const unread = unreadResult.status === 'fulfilled' ? unreadResult.value : undefined;
	return {
		preview: preview.error || !preview.data ? [] : preview.data.notifications,
		unreadCount: !unread || unread.error || !unread.data ? 0 : unread.data.count
	};
}
