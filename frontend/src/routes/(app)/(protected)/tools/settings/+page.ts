import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { getSettings } from '$lib/api/generated';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';
import { canManageSettings } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	const { user } = await parent();

	// Mirror the backend SETTINGS_MANAGE check before hitting the API, so the
	// page is not shown to users who would be rejected.
	if (!canManageSettings(user)) {
		error(403, 'У тебя нет доступа к настройкам фестиваля');
	}

	// The page reuses this key after saving so the loaded data stays fresh.
	depends('app:festival-settings');

	const client = createApiClient();
	const {
		data,
		error: requestError,
		response
	} = await getSettings({
		client,
		fetch,
		signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
	});

	if (requestError || !response?.ok || !data) {
		throwApiError(requestError, response, 'Не удалось загрузить настройки фестиваля');
	}

	return {
		title: 'Настройки фестиваля',
		settings: data
	};
};
