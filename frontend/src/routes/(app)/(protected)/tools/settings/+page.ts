import { throwQueryError } from '$lib/api/errors';
import { getSettingsOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
import { canManageSettings } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	// Mirror the backend SETTINGS_MANAGE check before hitting the API, so the
	// page is not shown to users who would be rejected.
	if (!canManageSettings(user)) {
		error(403, 'У тебя нет доступа к настройкам фестиваля');
	}

	// Warm the cache the page component reads; saving invalidates the same key.
	try {
		await queryClient.ensureQueryData(getSettingsOptions());
	} catch (requestError) {
		throwQueryError(requestError, 'Не удалось загрузить настройки фестиваля');
	}

	return { title: 'Настройки фестиваля' };
};
