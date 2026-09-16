import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { getVotingNomination } from '$lib/api/generated';
import { isBackendUnreachableStatus, isReachable, markReachable } from '$lib/services/reachability';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';
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
		} = await getVotingNomination({
			client,
			fetch,
			signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS),
			path: {
				nomination_code: params.nominationCode
			}
		});

		if (apiError || !data) {
			// A network failure (offline / timeout / abort) surfaces as an error with
			// no `response`; a gateway 5xx (502/503/504) is a live proxy over a dead
			// backend. Both mean unreachable — mirror the offline path above (honest
			// online-only state) instead of the misleading "Номинация не найдена".
			if (!response || isBackendUnreachableStatus(response.status)) {
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
