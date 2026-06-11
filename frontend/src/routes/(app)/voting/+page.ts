import { createApiClient } from '$lib/api';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const client = createApiClient();
	const { data, error: apiError, response } = await client.GET('/voting/nominations', { fetch });

	if (apiError) {
		console.error('Error fetching nominations:', apiError);
		error(response?.status ?? 500, 'Не удалось загрузить номинации');
	}

	return {
		title: 'Голосование',
		nominations: data?.nominations ?? []
	};
};
