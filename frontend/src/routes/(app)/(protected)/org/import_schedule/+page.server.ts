import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	const user = locals.user;
	const canImportSchedule = user?.role === 'org';

	if (!canImportSchedule) {
		error(403, 'У тебя нет доступа к импорту расписания');
	}

	return {};
};
