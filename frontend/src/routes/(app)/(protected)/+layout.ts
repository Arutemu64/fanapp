import { LOGIN_NEXT_PARAM } from '$lib/utils/auth';
import { redirect } from '@sveltejs/kit';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent, url }) => {
	const { user } = await parent();

	if (!user) {
		// A guest: send them to login, remembering where they were headed so
		// completeLogin can return them there (validated by sanitizeNextPath on the
		// way back).
		redirect(303, `/login?${LOGIN_NEXT_PARAM}=${encodeURIComponent(url.pathname + url.search)}`);
	}
};
