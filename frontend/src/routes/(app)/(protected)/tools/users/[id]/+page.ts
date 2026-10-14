import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { getApiErrorCode, throwApiError } from '#lib/api/errors.js';
import { getUserOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { queryForLoad } from '#lib/api/index.js';
import { m } from '#lib/paraglide/messages.js';
import { canReadUsers } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent, params }) => {
	const { queryClient, user } = await parent();

	// Mirror the backend users:read check before hitting the API, so the page is
	// not shown to users the endpoint would reject with a 403.
	if (!canReadUsers(user)) {
		error(403, m.user_card_forbidden());
	}

	// Staff-only operational data, like the directory: waits for a fresh copy.
	const data = await queryForLoad(queryClient, {
		...getUserOptions({ path: { user_id: params.id } }),
		staleTime: 0
	}).catch((apiError: unknown) => {
		if (getApiErrorCode(apiError) === 'USER_NOT_FOUND') {
			error(404, m.user_not_found());
		}
		return throwApiError(apiError, undefined, m.user_load_failed());
	});

	return {
		title: m.user_title(),
		back: { href: 'tools/users', label: m.users_back() } satisfies BackTarget,
		profile: data
	};
};
