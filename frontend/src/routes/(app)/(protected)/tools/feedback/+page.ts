import { listFeedbackInfiniteOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
import { FEEDBACK_PAGE_REQUEST_LIMIT } from '$lib/constants/feedback';
import { canReadFeedback } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	// The tools layout already gates the section to organisers; mirror the backend
	// FEEDBACK_READ check here so a user without the grant isn't shown a page the
	// list request would reject.
	if (!canReadFeedback(user)) {
		error(403, 'У тебя нет доступа к отзывам');
	}

	void queryClient.prefetchInfiniteQuery(
		listFeedbackInfiniteOptions({ query: { limit: FEEDBACK_PAGE_REQUEST_LIMIT } })
	);

	return { title: 'Отзывы' };
};
