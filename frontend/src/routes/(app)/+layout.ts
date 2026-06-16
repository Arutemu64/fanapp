import { createApiClient } from '$lib/api';
import { NOTIFICATION_PREVIEW_LIMIT } from '$lib/constants/notifications';
import { timeoutSignal, FIRST_PAINT_TIMEOUT_MS } from '$lib/utils/fetchTimeout';
import { isReachable, markReachable } from '$lib/services/reachability';
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
		return { notificationPreview: [] };
	}

	const client = createApiClient();

	// The bell is non-critical: on error/timeout (or offline) fall back to an empty
	// preview so the app shell still renders. The live SSE stream refreshes it once
	// the client reconnects.
	try {
		const { data, error } = await client.GET('/notifications/', {
			fetch,
			params: { query: { limit: NOTIFICATION_PREVIEW_LIMIT } },
			signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
		});
		markReachable(true);
		return { notificationPreview: error || !data ? [] : data.notifications };
	} catch {
		markReachable(false);
		return { notificationPreview: [] };
	}
};
