import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { throwApiError } from '#lib/api/errors.js';
import { getSettingsOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { canManageSettings } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	// Mirror the backend SETTINGS_MANAGE check before hitting the API, so the
	// page is not shown to users who would be rejected.
	if (!canManageSettings(user)) {
		error(403, 'У тебя нет доступа к настройкам фестиваля');
	}

	// The form is seeded once from this, so it waits for a fresh copy rather than
	// a cached one an edit would then overwrite.
	const settings = await queryClient
		.query({ ...getSettingsOptions(), staleTime: 0 })
		.catch((apiError: unknown) =>
			throwApiError(apiError, undefined, 'Не удалось загрузить настройки фестиваля')
		);

	return {
		title: 'Настройки фестиваля',
		back: { href: 'tools', label: 'Назад к инструментам' } satisfies BackTarget,
		settings
	};
};
