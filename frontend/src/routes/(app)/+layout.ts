import {
	countUnreadNotificationsOptions,
	listUserNotificationsOptions
} from '$lib/api/generated/@tanstack/svelte-query.gen';
import { NOTIFICATION_PREVIEW_LIMIT } from '$lib/constants/notifications';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	// The notification bell lives in the persistent app shell. Warm its preview and
	// unread count rather than awaiting them: awaiting would gate the shell's first
	// paint behind two more round-trips after `/me`, a pure waterfall. The bell
	// renders from its own queries the moment they resolve, and the live SSE stream
	// invalidates them thereafter, so a slightly late seed is invisible.
	//
	// The preview feeds the dropdown list; the unread count is a separate query
	// because the badge must reflect the true total, not the capped preview length
	// (a preview of 5 can hide dozens of unread items). Guests never see the bell.
	if (!user) return;

	void queryClient.prefetchQuery(
		listUserNotificationsOptions({ query: { limit: NOTIFICATION_PREVIEW_LIMIT } })
	);
	void queryClient.prefetchQuery(countUnreadNotificationsOptions());
};
