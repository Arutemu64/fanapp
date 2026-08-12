import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { isReachable, markReachable } from '$lib/services/reachability';
import { isHttpError } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	// Voting is a live, online-only surface: casting a vote is a mutation, and the
	// open/closed and already-voted state must never be shown stale (a cached ballot
	// you can't submit is a dead end). So it is deliberately not cached. When the
	// backend is known unreachable, skip the doomed request and show an honest
	// "online only" state instead of a generic error that implies offline data.
	if (!isReachable()) {
		return { title: 'Голосование', nominations: [], offlineOnly: true };
	}

	const client = createApiClient();

	try {
		const { data, error: apiError, response } = await client.GET('/voting/nominations', { fetch });

		if (apiError) {
			throwApiError(apiError, response, 'Не удалось загрузить номинации');
		}

		return {
			title: 'Голосование',
			nominations: data?.nominations ?? [],
			offlineOnly: false
		};
	} catch (err) {
		// A reachable failure surfaced by throwApiError: re-throw so the error page
		// shows the mapped status. Anything else is a network failure (offline /
		// timeout) — mark us unreachable and fall to the honest online-only state.
		if (isHttpError(err)) throw err;
		markReachable(false);
		return { title: 'Голосование', nominations: [], offlineOnly: true };
	}
};
