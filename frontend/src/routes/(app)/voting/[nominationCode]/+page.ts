import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch, depends }) => {
	depends('app:voting:nomination');

	const client = createApiClient();
	const {
		data,
		error: apiError,
		response
	} = await client.GET('/voting/nominations/{nomination_code}', {
		fetch,
		params: {
			path: {
				nomination_code: params.nominationCode
			}
		}
	});

	if (apiError || !data) {
		throwApiError(apiError, response, 'Номинация не найдена');
	}

	return {
		title: 'Голосование',
		nomination: data
	};
};
