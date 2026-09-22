import { scheduleChangesFeedOptions } from '$lib/api/feeds';
import { canManageSchedule } from '$lib/utils/permissions';
import { error, redirect } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	if (!user) {
		redirect(303, '/login');
	}

	if (!canManageSchedule(user)) {
		error(403, 'У вас нет доступа к этой странице');
	}

	await queryClient.prefetchInfiniteQuery(scheduleChangesFeedOptions());

	return { title: 'Изменения программы' };
};
