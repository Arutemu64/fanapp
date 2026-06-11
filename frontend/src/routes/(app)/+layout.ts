import { createApiClient } from '$lib/api';
import { NOTIFICATION_PREVIEW_LIMIT } from '$lib/constants/notifications';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ fetch, depends, parent }) => {
	// The notification bell lives in the persistent app shell. Load its preview
	// here so the unread badge is rendered correctly on the first SSR paint
	// instead of popping in after the client mounts and fetches.
	depends('app:notifications');

	const { user } = await parent();

	// Guests never see the bell, so skip the request entirely.
	if (!user) {
		return { notificationPreview: [] };
	}

	const client = createApiClient();
	const { data, error } = await client.GET('/notifications/', {
		fetch,
		params: { query: { limit: NOTIFICATION_PREVIEW_LIMIT } }
	});

	// The bell is non-critical: on error fall back to an empty preview and let the
	// live SSE stream refresh it once the client connects.
	return {
		notificationPreview: error || !data ? [] : data.notifications
	};
};
