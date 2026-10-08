import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { throwApiError } from '#lib/api/errors.js';
import { getVotingDashboard } from '#lib/api/generated/index.js';
import { createApiClient } from '#lib/api/index.js';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '#lib/utils/fetchTimeout.js';
import { canManageVoting } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, parent }) => {
	const { user } = await parent();

	// Mirror the backend voting:manage check before hitting the API, so the page
	// is not shown to users the endpoint would reject with a 403.
	if (!canManageVoting(user)) {
		error(403, 'У тебя нет доступа к управлению голосованием');
	}

	const client = createApiClient();
	const {
		data,
		error: requestError,
		response
	} = await getVotingDashboard({
		client,
		fetch,
		signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
	});

	if (requestError || !response?.ok || !data) {
		throwApiError(requestError, response, 'Не удалось загрузить панель голосования');
	}

	return {
		title: 'Голосование',
		back: { href: 'tools', label: 'Назад к инструментам' } satisfies BackTarget,
		dashboard: data
	};
};
