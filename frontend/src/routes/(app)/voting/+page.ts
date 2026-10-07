import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { listVotingNominations } from '$lib/api/generated';
import { REQUIRED_READ_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const client = createApiClient();
	const {
		data,
		error: apiError,
		response
	} = await listVotingNominations({
		client,
		fetch,
		signal: timeoutSignal(REQUIRED_READ_TIMEOUT_MS)
	});

	if (apiError) {
		throwApiError(apiError, response, 'Не удалось загрузить номинации');
	}

	return {
		title: 'Голосование',
		nominations: data?.nominations ?? []
	};
};
