import { listScheduleChangesInfiniteOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
import { SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT } from '$lib/constants/schedule_changes';
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

	await queryClient.prefetchInfiniteQuery(
		listScheduleChangesInfiniteOptions({
			query: { limit: SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT }
		})
	);

	return { title: 'Изменения программы' };
};
