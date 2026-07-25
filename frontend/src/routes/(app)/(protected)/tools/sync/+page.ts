import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { canRunSync } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent, fetch, depends }) => {
	depends('app:sync-sources');

	const { user } = await parent();

	// Mirror the backend SYNC_RUN check so the page is not shown to users who
	// would be rejected on submit.
	if (!canRunSync(user)) {
		error(403, 'У тебя нет доступа к синхронизации');
	}

	const client = createApiClient();
	const { data, error: apiError, response } = await client.GET('/sync/sources', { fetch });

	if (apiError || !response.ok || !data) {
		throwApiError(apiError, response, 'Не удалось загрузить состояние синхронизации');
	}

	return {
		title: 'Синхронизация',
		sources: data
	};
};
