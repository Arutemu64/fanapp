import { error } from '@sveltejs/kit';
import { canImportSchedule } from '$lib/utils/permissions';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	// Mirror the backend SCHEDULE_IMPORT check so the page is not shown to users
	// who would be rejected on submit.
	if (!canImportSchedule(user)) {
		error(403, 'У тебя нет доступа к импорту расписания');
	}

	return {
		title: 'Импорт расписания'
	};
};
