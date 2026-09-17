import { canManageSchedule } from '$lib/utils/permissions';
import { error, redirect } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	if (!user) {
		redirect(303, '/login');
	}

	if (!canManageSchedule(user)) {
		error(403, 'У вас нет доступа к этой странице');
	}

	// The feed component owns the request as an infinite query. Staff-only
	// operational data, so it is never cached for offline (see
	// PERSISTED_OPERATIONS in $lib/api/queryClient).
	return { title: 'Изменения программы' };
};
