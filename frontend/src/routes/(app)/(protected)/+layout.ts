import { error, redirect } from '@sveltejs/kit';

import { m } from '#lib/paraglide/messages.js';
import { currentUserOptions } from '#lib/services/identity.js';
import { isReachable, probeReachability } from '#lib/services/reachability.js';
import { LOGIN_NEXT_PARAM } from '#lib/utils/auth.js';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent, url }) => {
	const { queryClient } = await parent();
	const user = queryClient.getQueryData(currentUserOptions().queryKey);

	if (!user) {
		if (isReachable()) await probeReachability();
		if (!isReachable()) {
			error(503, m.connection_no_server());
		}

		redirect(303, `/login?${LOGIN_NEXT_PARAM}=${encodeURIComponent(url.pathname + url.search)}`);
	}

	return { user };
};
