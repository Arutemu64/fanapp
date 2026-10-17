import { redirect } from '@sveltejs/kit';

import { currentUserOptions } from '#lib/services/identity.js';
import { LOGIN_NEXT_PARAM, sanitizeNextPath } from '#lib/utils/auth.js';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent, url }) => {
	// The root load settled identity into the cache before any guard runs.
	const { queryClient } = await parent();
	const user = queryClient.getQueryData(currentUserOptions().queryKey);

	if (user) {
		// Already signed in: honor a pending `next` target (e.g. a login link
		// opened after the session was already established) instead of always
		// landing home. sanitizeNextPath keeps this an in-app path.
		redirect(303, sanitizeNextPath(url.searchParams.get(LOGIN_NEXT_PARAM)) ?? '/');
	}

	return {};
};
