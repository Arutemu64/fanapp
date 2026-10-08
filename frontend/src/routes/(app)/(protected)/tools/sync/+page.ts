import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { throwApiError } from '#lib/api/errors.js';
import { getSyncSources } from '#lib/api/generated/index.js';
import { createApiClient } from '#lib/api/index.js';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '#lib/utils/fetchTimeout.js';
import { canRunSync } from '#lib/utils/permissions.js';

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
	const {
		data,
		error: apiError,
		response
	} = await getSyncSources({
		client,
		fetch,
		signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
	});

	if (apiError || !response?.ok || !data) {
		throwApiError(apiError, response, 'Не удалось загрузить состояние синхронизации');
	}

	return {
		title: 'Синхронизация',
		back: { href: 'tools', label: 'Назад к инструментам' } satisfies BackTarget,
		sources: data
	};
};
