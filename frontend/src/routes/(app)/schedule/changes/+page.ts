import { error, redirect } from '@sveltejs/kit';
import { createApiClient } from '$lib/api';
import { canManageSchedule } from '$lib/utils/permissions';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	const { user } = await parent();

	if (!user) {
		redirect(303, '/login');
	}

	if (!canManageSchedule(user)) {
		error(403, 'У вас нет доступа к этой странице');
	}

	depends('app:schedule:changes');

	const client = createApiClient();

	// Staff-only operational feed: stale data would misrepresent live state, so
	// no offline cache here — fail hard when unreachable instead.
	const { data, error: fetchError } = await client.GET('/schedule/changes/', { fetch });
	if (fetchError || !data) {
		error(503, 'Не удалось загрузить изменения расписания');
	}

	return { title: 'Изменения расписания', schedule_changes: data.schedule_changes ?? [] };
};
