import { canGenerateTickets } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	// Mirror the backend TICKETS_GENERATE check so the page is not shown to
	// users who would be rejected on submit.
	if (!canGenerateTickets(user)) {
		error(403, 'У тебя нет доступа к генерации билетов');
	}

	return {
		title: 'Генерация билетов'
	};
};
