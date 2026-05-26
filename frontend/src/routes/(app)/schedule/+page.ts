import { error } from '@sveltejs/kit';
import { createApiClient } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends }) => {
	depends('app:schedule');
	const client = createApiClient();
	const { data, error: fetchError, response } = await client.GET('/schedule/', { fetch });

	if (fetchError) {
		error(response.status, 'Не удалось загрузить расписание');
	}

	return {
		schedule: data?.schedule ?? []
	};
};
