import { error, redirect } from '@sveltejs/kit';

import { m } from '#lib/paraglide/messages.js';
import { currentUserOptions } from '#lib/services/identity.js';
import { LOGIN_NEXT_PARAM, sanitizeNextPath } from '#lib/utils/auth.js';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent, url }) => {
	const { queryClient, identityReady } = await parent();
	await identityReady;
	const user = queryClient.getQueryData(currentUserOptions().queryKey);

	if (user === undefined) {
		error(503, m.error_identity_check_failed());
	}
	if (user !== null) {
		redirect(303, sanitizeNextPath(url.searchParams.get(LOGIN_NEXT_PARAM)) ?? '/');
	}

	return {};
};
