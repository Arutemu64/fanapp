import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { canManageVoting } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, parent }) => {
	const { user } = await parent();

	// Mirror the backend voting:manage check before hitting the API, so the page
	// is not shown to users the endpoint would reject with a 403.
	if (!canManageVoting(user)) {
		error(403, 'У тебя нет доступа к управлению голосованием');
	}

	const client = createApiClient();
	const { data, error: requestError, response } = await client.GET('/voting/dashboard', { fetch });

	if (requestError || !response.ok || !data) {
		throwApiError(requestError, response, 'Не удалось загрузить панель голосования');
	}

	return {
		title: 'Голосование',
		dashboard: data
	};
};
