import { error } from '@sveltejs/kit';
import { client } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends }) => {
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
