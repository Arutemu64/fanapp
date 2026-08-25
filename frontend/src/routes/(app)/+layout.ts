import { createApiClient } from '$lib/api';
import { NOTIFICATION_PREVIEW_LIMIT } from '$lib/constants/notifications';
import { isReachable, markReachable } from '$lib/services/reachability';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ fetch, depends, parent }) => {
	// The notification bell lives in the persistent app shell. Load its preview
	// here so the unread badge is rendered correctly on the first paint instead
	// of popping in after the client mounts and fetches.
	depends('app:notifications');

	const { user } = await parent();

	// Guests never see the bell; when unreachable we can't load it. Either way the
	// shell must render fast, so skip the request and let the SSE stream fill it later.
	if (!user || !isReachable()) {
		return { notificationPreview: [], notificationUnreadCount: 0 };
	}

	const client = createApiClient();

	// The bell is non-critical: on error/timeout (or offline) fall back to an empty
	// preview so the app shell still renders. The live SSE stream refreshes it once
	// the client reconnects. The preview feeds the dropdown list; the unread count
	// is fetched separately because the badge must reflect the true total, not the
	// capped preview length (a preview of 5 can hide dozens of unread items).
	try {
		const [preview, unread] = await Promise.all([
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
		markReachable(true);
		return {
			notificationPreview: preview.error || !preview.data ? [] : preview.data.notifications,
			notificationUnreadCount: unread.error || !unread.data ? 0 : unread.data.count
		};
	} catch {
		markReachable(false);
		return { notificationPreview: [], notificationUnreadCount: 0 };
	}
};
