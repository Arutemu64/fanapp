import { throwQueryError } from '$lib/api/errors';
import { getSyncSourcesOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
import { canRunSync } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	// Mirror the backend SYNC_RUN check so the page is not shown to users who
	// would be rejected on submit.
	if (!canRunSync(user)) {
		error(403, 'У тебя нет доступа к синхронизации');
	}

	try {
		await queryClient.ensureQueryData(getSyncSourcesOptions());
	} catch (requestError) {
		throwQueryError(requestError, 'Не удалось загрузить состояние синхронизации');
	}

	return { title: 'Синхронизация' };
};
