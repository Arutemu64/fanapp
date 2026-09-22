import { throwApiError } from '$lib/api/errors';
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

	// Awaited: this page seeds its form/table state from the response at mount, so
	// it must be in the cache before the component runs. A failure here is a real
	// server error — the tools layout already redirects offline visitors to the hub
	// — so it becomes the error page rather than an inline state.
	await queryClient.ensureQueryData(getSyncSourcesOptions()).catch((requestError: unknown) => {
		throwApiError(requestError, undefined, 'Не удалось загрузить состояние синхронизации');
	});

	return { title: 'Синхронизация' };
};
