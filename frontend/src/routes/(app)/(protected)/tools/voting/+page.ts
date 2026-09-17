import { throwQueryError } from '$lib/api/errors';
import { getVotingDashboardOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
import { canManageVoting } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	// Mirror the backend voting:manage check before hitting the API, so the page
	// is not shown to users the endpoint would reject with a 403.
	if (!canManageVoting(user)) {
		error(403, 'У тебя нет доступа к управлению голосованием');
	}

	try {
		await queryClient.ensureQueryData(getVotingDashboardOptions());
	} catch (requestError) {
		throwQueryError(requestError, 'Не удалось загрузить панель голосования');
	}

	return { title: 'Голосование' };
};
