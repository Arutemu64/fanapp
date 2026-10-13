import { error, redirect } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { currentUserOptions } from '#lib/api/index.js';
import { canManageSchedule } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient } = await parent();
	const user = queryClient.getQueryData(currentUserOptions().queryKey) ?? null;

	if (!user) {
		redirect(303, '/login');
	}

	if (!canManageSchedule(user)) {
		error(403, 'У тебя нет доступа к этой странице');
	}

	return {
		title: 'Изменения программы',
		back: { href: 'schedule', label: 'Назад к программе' } satisfies BackTarget
	};
};
