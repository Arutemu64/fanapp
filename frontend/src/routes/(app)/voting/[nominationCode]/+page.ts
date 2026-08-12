import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { isReachable, markReachable } from '$lib/services/reachability';
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
