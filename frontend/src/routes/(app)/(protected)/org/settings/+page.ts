import { error } from '@sveltejs/kit';
import { createApiClient } from '$lib/api';
import { canManageSettings } from '$lib/utils/permissions';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	const { user } = await parent();

	// Mirror the backend SETTINGS_MANAGE check before hitting the API, so the
	// page is not shown to users who would be rejected.
	if (!canManageSettings(user)) {
		error(403, 'У тебя нет доступа к настройкам фестиваля');
	}

	// The page reuses this key after saving so the SSR-loaded data stays fresh.
	depends('app:festival-settings');

	const client = createApiClient();
	const { data, error: requestError, response } = await client.GET('/settings', { fetch });

	if (requestError || !response.ok || !data) {
		console.error('Festival settings load failed:', requestError ?? response.statusText);

		if (response.status === 401) {
			error(401, 'Нужно войти в аккаунт заново');
		}

		if (response.status === 403) {
			error(403, 'У тебя нет доступа к настройкам фестиваля');
		}

		if (response.status === 404) {
			error(404, 'Настройки фестиваля не найдены');
		}

		error(500, 'Не удалось загрузить настройки фестиваля');
	}

	return {
		title: 'Настройки фестиваля',
		settings: data
	};
};
