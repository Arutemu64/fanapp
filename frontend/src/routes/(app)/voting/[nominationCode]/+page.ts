import { createApiClient } from '$lib/api';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch, depends }) => {
	depends('app:voting:nomination');

	const client = createApiClient();
	const { data, error: apiError } = await client.GET('/voting/nominations/{nomination_code}', {
		fetch,
		params: {
			path: {
				nomination_code: params.nominationCode
			}
		}
	});

	if (apiError || !data) {
		console.error('Error fetching nomination:', apiError);
		error(404, 'Номинация не найдена');
	}

	return {
		title: 'Голосование',
		nomination: data
	};
};
