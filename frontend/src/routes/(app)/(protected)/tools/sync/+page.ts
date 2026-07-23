import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { canRunSyncs } from '$lib/utils/permissions';
import { error, redirect } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	const { user } = await parent();

	if (!user) {
		redirect(303, '/login');
	}

	if (!canRunSyncs(user)) {
		error(403, 'У тебя нет доступа к этой странице');
	}

	depends('app:sync');

	const client = createApiClient();

	// Staff-only operational feed: stale data would misrepresent live state, so
	// no offline cache here — fail hard when unreachable instead.
	const { data, error: fetchError, response } = await client.GET('/sync/status', { fetch });
	if (fetchError || !data) {
		throwApiError(fetchError, response, 'Не удалось загрузить статус синхронизации');
	}

	return {
		title: 'Синхронизация',
		sources: data.sources
	};
};
