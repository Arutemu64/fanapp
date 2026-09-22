import { broadcastsFeedOptions } from '$lib/api/feeds';
import { canSendNotifications } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	// Mirror the backend NOTIFICATIONS_SEND check so the page is not shown to
	// users who would be rejected on submit.
	if (!canSendNotifications(user)) {
		error(403, 'У тебя нет доступа к рассылке уведомлений');
	}

	// Sent history, fire-and-forget: a failure must not block the composer, so the
	// history section renders its own error state while the form stays usable.
	void queryClient.prefetchInfiniteQuery(broadcastsFeedOptions());

	return { title: 'Рассылка уведомлений' };
};
