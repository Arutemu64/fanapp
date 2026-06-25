import { isReachable } from '$lib/services/reachability';
import { error, redirect } from '@sveltejs/kit';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent }) => {
	const { user } = await parent();

	if (!user) {
		// A null user has two very different causes. Only redirect to login when the
		// server is reachable and actually told us we're a guest. When offline with
		// no cached identity we can't prove the user is logged out — their session
		// cookie may still be valid — so bouncing them to a login page that can't
		// work offline would log out an authenticated user on a flaky connection.
		// Show the offline state instead (ErrorState reframes this as "Нет соединения").
		if (!isReachable()) {
			error(503, 'Нет соединения');
		}

		// Reachable and still no user: a genuine guest — send them to login.
		redirect(303, '/login');
	}
};
