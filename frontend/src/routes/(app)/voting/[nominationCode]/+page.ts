import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { isBackendUnreachableStatus, isReachable, markReachable } from '$lib/services/reachability';
import { isHttpError } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch, depends }) => {
	depends('app:voting:nomination');

	// Online-only like the nominations list (see ../+page.ts): voting is a live
	// mutation surface and is deliberately not cached, so a known-unreachable
	// backend gets an honest "online only" state, not a stale ballot.
	if (!isReachable()) {
		return { title: 'Голосование', nomination: undefined, offlineUnavailable: true };
	}

	const client = createApiClient();

	try {
		const {
			data,
			error: apiError,
			response
		} = await client.GET('/voting/nominations/{nomination_code}', {
			fetch,
			params: {
				path: {
					nomination_code: params.nominationCode
				}
			}
		});

		if (apiError || !data) {
			// A gateway 5xx (502/503/504) is the backend being unreachable behind a
			// live proxy, not a missing nomination — treat it like the offline path
			// above (honest online-only state) instead of throwing a misleading
			// "Номинация не найдена". throwApiError already marks us unreachable and
			// drops the Sentry noise for these; short-circuiting here keeps the
			// tailored voting empty state instead of the generic error page.
			if (response && isBackendUnreachableStatus(response.status)) {
				markReachable(false);
				return { title: 'Голосование', nomination: undefined, offlineUnavailable: true };
			}
			throwApiError(apiError, response, 'Номинация не найдена');
		}

		return {
			title: 'Голосование',
			nomination: data,
			offlineUnavailable: false
		};
	} catch (err) {
		if (isHttpError(err)) throw err;
		markReachable(false);
		return { title: 'Голосование', nomination: undefined, offlineUnavailable: true };
	}
};
