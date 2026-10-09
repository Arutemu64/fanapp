import { throwApiError } from '#lib/api/errors.js';
import { listVotingNominations } from '#lib/api/generated/index.js';
import { createApiClient } from '#lib/api/index.js';
import { isReachable, isUnreachableResponse } from '#lib/services/reachability.js';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '#lib/utils/fetchTimeout.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	// Voting is a live, online-only surface: casting a vote is a mutation, and the
	// open/closed and already-voted state must never be shown stale (a cached ballot
	// you can't submit is a dead end). So it is deliberately not cached. When the
	// backend is known unreachable, skip the doomed request and show an honest
	// "online only" state instead of a generic error that implies offline data.
	const offlineState = { title: 'Голосование', nominations: [], offlineUnavailable: true };
	if (!isReachable()) return offlineState;

	const {
		data,
		error: apiError,
		response
	} = await listVotingNominations({
		client: createApiClient(),
		fetch,
		signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
	});

	if (apiError) {
		// Not reaching the backend is the same situation as the offline path above.
		// A real answer (4xx/5xx) keeps its mapped status on the error page.
		if (isUnreachableResponse(response)) return offlineState;
		throwApiError(apiError, response, 'Не удалось загрузить номинации');
	}

	return {
		title: 'Голосование',
		nominations: data?.nominations ?? [],
		offlineUnavailable: false
	};
};
