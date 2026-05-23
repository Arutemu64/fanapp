import { error, redirect } from '@sveltejs/kit';
import { client } from '$lib/api';
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

	const {
		data,
		error: fetchError,
		response
	} = await client.GET('/schedule/changes/', {
		fetch
	});

	if (fetchError) {
		error(response.status, 'Не удалось загрузить изменения расписания');
	}

	return {
		schedule_changes: data?.schedule_changes ?? []
	};
};
