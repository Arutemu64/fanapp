import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { throwApiError } from '#lib/api/errors.js';
import { getSettings } from '#lib/api/generated/index.js';
import { createApiClient } from '#lib/api/index.js';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '#lib/utils/fetchTimeout.js';
import { canManageSettings } from '#lib/utils/permissions.js';

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
		back: { href: 'tools', label: 'Назад к инструментам' } satisfies BackTarget,
		settings: data
	};
};
