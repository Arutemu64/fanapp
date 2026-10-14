import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { canReadUsers } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	// The tools layout gates the section to organisers; mirror the backend
	// users:read check here so a user without the grant isn't shown a page the
	// list request would reject with a 403.
	if (!canReadUsers(user)) {
		error(403, 'У тебя нет доступа к списку пользователей');
	}

	return {
		title: 'Пользователи',
		back: { href: 'tools', label: 'Назад к инструментам' } satisfies BackTarget
	};
};
