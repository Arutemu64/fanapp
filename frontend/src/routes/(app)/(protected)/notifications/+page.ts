import { listUserNotificationsInfiniteOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
import { NOTIFICATION_PAGE_REQUEST_LIMIT } from '$lib/constants/notifications';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient } = await parent();

	// The feed paginates, so it is one infinite query rather than a first page plus
	// hand-rolled "load more" state: TanStack owns the pages, their dedupe and the
	// persisted copy, and the page component reads `hasNextPage` from it.
	await queryClient.prefetchInfiniteQuery(
		listUserNotificationsInfiniteOptions({ query: { limit: NOTIFICATION_PAGE_REQUEST_LIMIT } })
	);

	return { title: 'Уведомления' };
};
