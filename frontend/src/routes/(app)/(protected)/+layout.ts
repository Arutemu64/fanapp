import { LOGIN_NEXT_PARAM } from '$lib/utils/auth';
import { error, redirect } from '@sveltejs/kit';
import { onlineManager } from '@tanstack/svelte-query';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent, url }) => {
	const { user } = await parent();

	if (!user) {
		// A null user has two very different causes. Only redirect to login when we
		// are online and the server actually told us we're a guest. When offline with
		// no cached identity we can't prove the user is logged out — their session
		// cookie may still be valid — so bouncing them to a login page that can't
		// work offline would log out an authenticated user on a flaky connection.
		// Show the offline state instead (ErrorState reframes this into a
		// "нет интернета" or "нет связи с сервером" page).
		if (!onlineManager.isOnline()) {
			// A 503 renders the offline ErrorState. hooks.client.ts drops every 5xx
			// HttpError from Sentry, so this expected offline blip never becomes a
			// GlitchTip issue.
			error(503, { message: 'Нет связи с сервером' });
		}

		// Online and still no user: a genuine guest — send them to login,
		// remembering where they were headed so completeLogin can return them
		// there (validated by sanitizeNextPath on the way back).
		redirect(303, `/login?${LOGIN_NEXT_PARAM}=${encodeURIComponent(url.pathname + url.search)}`);
	}
};
