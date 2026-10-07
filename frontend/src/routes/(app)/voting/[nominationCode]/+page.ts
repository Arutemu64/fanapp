import type { BackTarget } from '$lib/types/navigation';

import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { getVotingNomination } from '$lib/api/generated';

import type { PageLoad } from './$types';

const back = { href: '/voting', label: 'Назад к номинациям' } satisfies BackTarget;

export const load: PageLoad = async ({ params, fetch, depends }) => {
	depends('app:voting:nomination');

	const client = createApiClient();
	const {
		data,
		error: apiError,
		response
	} = await getVotingNomination({
		client,
		fetch,
		path: {
			nomination_code: params.nominationCode
		}
	});

	if (apiError || !data) {
		throwApiError(apiError, response, 'Номинация не найдена');
	}

	// The nomination is the screen's name, so it titles the navbar.
	return {
		title: data.title,
		back,
		nomination: data
	};
};
