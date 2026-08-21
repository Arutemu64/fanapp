import { createApiClient } from '$lib/api';
import { loadOnline, throwApiError } from '$lib/api/errors';
import { FEEDBACK_PAGE_REQUEST_LIMIT, FEEDBACK_PAGE_SIZE } from '$lib/constants/feedback';
import { canReadFeedback } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, parent }) => {
	const { user } = await parent();

	// The tools layout already gates the section to organisers; mirror the backend
	// FEEDBACK_READ check here so a user without the grant isn't shown a page the
	// list request would reject.
	if (!canReadFeedback(user)) {
		error(403, 'У тебя нет доступа к отзывам');
	}

	const client = createApiClient();

	// Staff-only operational feed: stale data would misrepresent live state, so no
	// offline cache here — loadOnline fails to the offline page when unreachable.
	// Over-fetch one item so the client can tell whether a next page exists.
	const feedback = await loadOnline(async () => {
		const {
			data,
			error: fetchError,
			response
		} = await client.GET('/feedback/', {
			fetch,
			params: { query: { limit: FEEDBACK_PAGE_REQUEST_LIMIT, offset: 0 } }
		});
		if (fetchError || !data) {
			throwApiError(fetchError, response, 'Не удалось загрузить отзывы');
		}

		return data.feedback ?? [];
	});

	return {
		title: 'Отзывы',
		feedback: feedback.slice(0, FEEDBACK_PAGE_SIZE),
		hasMore: feedback.length > FEEDBACK_PAGE_SIZE
	};
};
