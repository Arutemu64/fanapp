import { LOGIN_NEXT_PARAM, sanitizeNextPath } from '$lib/utils/auth';
import { redirect } from '@sveltejs/kit';

import type { LayoutLoad, LayoutLoadEvent } from './$types';

export const load: LayoutLoad = async ({ parent, url }: LayoutLoadEvent) => {
	// Reuse the user from the root layout data so this guard works
	// on first load and on later client-side navigations.
	const { user } = await parent();

	if (user) {
		// Already signed in: honor a pending `next` target (e.g. a login link
		// opened after the session was already established) instead of always
		// landing home. sanitizeNextPath keeps this an in-app path.
		redirect(303, sanitizeNextPath(url.searchParams.get(LOGIN_NEXT_PARAM)) ?? '/');
	}

	return {};
};
