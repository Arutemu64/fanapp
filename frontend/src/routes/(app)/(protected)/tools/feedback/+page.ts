import { canReadFeedback } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	// The tools layout already gates the section to organisers; mirror the backend
	// FEEDBACK_READ check here so a user without the grant isn't shown a page the
	// list request would reject.
	if (!canReadFeedback(user)) {
		error(403, 'У тебя нет доступа к отзывам');
	}

	// The feed component owns the request: it is an infinite query, so the first
	// page is just its first page rather than a separately loaded snapshot.
	return { title: 'Отзывы' };
};
