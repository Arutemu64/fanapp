import type { BackTarget } from '#lib/types/navigation.js';

import { throwApiError } from '#lib/api/errors.js';
import { getVotingNomination } from '#lib/api/generated/index.js';
import { createApiClient } from '#lib/api/index.js';
import { isReachable, isUnreachableResponse } from '#lib/services/reachability.js';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '#lib/utils/fetchTimeout.js';

import type { PageLoad } from './$types';

const back = { href: 'voting', label: 'Назад к номинациям' } satisfies BackTarget;

export const load: PageLoad = async ({ params, fetch, depends }) => {
	depends('app:voting:nomination');

	// Online-only like the nominations list (see ../+page.ts): voting is a live
	// mutation surface and is deliberately not cached, so a known-unreachable
	// backend gets an honest "online only" state, not a stale ballot.
	const offlineState = {
		title: 'Голосование',
		back,
		nomination: undefined,
		offlineUnavailable: true
	};
	if (!isReachable()) return offlineState;

	const {
		data,
		error: apiError,
		response
	} = await getVotingNomination({
		client: createApiClient(),
		fetch,
		signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS),
		path: {
			nomination_code: params.nominationCode
		}
	});

	if (apiError || !data) {
		// Not reaching the backend is the same situation as the offline path above,
		// not the misleading "Номинация не найдена".
		if (isUnreachableResponse(response)) return offlineState;
		throwApiError(apiError, response, 'Номинация не найдена');
	}

	// The nomination is the screen's name, so it titles the navbar; the generic
	// 'Голосование' above covers the states with no nomination to name.
	return {
		title: data.title,
		back,
		nomination: data,
		offlineUnavailable: false
	};
};
