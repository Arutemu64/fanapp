import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { throwApiError } from '#lib/api/errors.js';
import { listFeedback } from '#lib/api/generated/index.js';
import { createApiClient } from '#lib/api/index.js';
import { FEEDBACK_PAGE_REQUEST_LIMIT, FEEDBACK_PAGE_SIZE } from '#lib/constants/feedback.js';
import { canReadFeedback } from '#lib/utils/permissions.js';

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

	// Staff-only operational feed: stale data would misrepresent live state, so
	// no offline cache here — fail hard when unreachable instead.
	// Over-fetch one item so the client can tell whether a next page exists.
	const {
		data,
		error: fetchError,
		response
	} = await listFeedback({
		client,
		fetch,
		query: { limit: FEEDBACK_PAGE_REQUEST_LIMIT, offset: 0 }
	});
	if (fetchError || !data) {
		throwApiError(fetchError, response, 'Не удалось загрузить отзывы');
	}

	const feedback = data.feedback ?? [];
	return {
		title: 'Отзывы',
		back: { href: 'tools', label: 'Назад к инструментам' } satisfies BackTarget,
		feedback: feedback.slice(0, FEEDBACK_PAGE_SIZE),
		hasMore: feedback.length > FEEDBACK_PAGE_SIZE
	};
};
