import { redirect } from '@sveltejs/kit';

import { currentUserOptions } from '#lib/services/identity.js';
import { LOGIN_NEXT_PARAM, sanitizeNextPath } from '#lib/utils/auth.js';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent, url }) => {
	const { queryClient } = await parent();
	const user = queryClient.getQueryData(currentUserOptions().queryKey);

	if (user) {
		redirect(303, sanitizeNextPath(url.searchParams.get(LOGIN_NEXT_PARAM)) ?? '/');
	}

	return {};
};
