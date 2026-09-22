import { notificationsFeedOptions } from '$lib/api/feeds';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient } = await parent();

	// The feed paginates, so it is one infinite query rather than a first page plus
	// hand-rolled "load more" state: TanStack owns the pages, their dedupe and the
	// persisted copy, and the page component reads `hasNextPage` from it.
	await queryClient.prefetchInfiniteQuery(notificationsFeedOptions());

	return { title: 'Уведомления' };
};
