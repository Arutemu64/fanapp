import { error, redirect } from '@sveltejs/kit';

import { currentUserOptions } from '#lib/api/index.js';
import { m } from '#lib/paraglide/messages.js';
import { isReachable, probeReachability } from '#lib/services/reachability.js';
import { LOGIN_NEXT_PARAM } from '#lib/utils/auth.js';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent, url }) => {
	// The root load settled identity into the cache before any guard runs.
	const { queryClient } = await parent();
	const user = queryClient.getQueryData(currentUserOptions().queryKey);

	if (!user) {
		// A null user has two very different causes. Only redirect to login when the
		// server is reachable and actually told us we're a guest. When offline with
		// no cached identity we can't prove the user is logged out — their session
		// cookie may still be valid — so bouncing them to a login page that can't
		// work offline would log out an authenticated user on a flaky connection.
		// Show the offline state instead (ErrorState reframes this into a
		// "нет интернета" or "нет связи с сервером" page from live reachability).
		// Ask the probe rather than trust the last verdict: on a cold start the API
		// interceptors that keep it current aren't installed yet (the root layout
		// mounts after this load), so `isReachable()` still holds its optimistic
		// default. A probe already running is joined.
		if (isReachable()) await probeReachability();
		if (!isReachable()) {
			// hooks.client.ts drops every 5xx HttpError from Sentry, so this expected
			// offline blip never becomes a GlitchTip issue.
			error(503, m.connection_no_server());
		}

		// Reachable and still no user: a genuine guest — send them to login,
		// remembering where they were headed so Session.loggedIn can return them
		// there (validated by sanitizeNextPath on the way back).
		redirect(303, `/login?${LOGIN_NEXT_PARAM}=${encodeURIComponent(url.pathname + url.search)}`);
	}

	// A snapshot for the permission checks in the loads below, which run on every
	// navigation; components read the live user from the query.
	return { user };
};
