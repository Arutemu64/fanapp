import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { canManageSchedule } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

// Staff-only, so it lives in (protected): the URL stays /schedule/changes, and a
// session that expires while it is open hands it over to /login like any other
// members-only screen.
export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	if (!canManageSchedule(user)) {
		error(403, 'У тебя нет доступа к этой странице');
	}

	return {
		title: 'Изменения программы',
		back: { href: 'schedule', label: 'Назад к программе' } satisfies BackTarget
	};
};
