import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { isBackendUnreachableStatus, isReachable, markReachable } from '$lib/services/reachability';
import { isHttpError } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	// Voting is a live, online-only surface: casting a vote is a mutation, and the
	// open/closed and already-voted state must never be shown stale (a cached ballot
	// you can't submit is a dead end). So it is deliberately not cached. When the
	// backend is known unreachable, skip the doomed request and show an honest
	// "online only" state instead of a generic error that implies offline data.
	if (!isReachable()) {
		return { title: 'Голосование', nominations: [], offlineUnavailable: true };
	}

	const client = createApiClient();

	try {
		const { data, error: apiError, response } = await client.GET('/voting/nominations', { fetch });

		if (apiError) {
			// A gateway 5xx (502/503/504) is the backend being unreachable behind a
			// live proxy, not a real load failure — treat it like the offline path
			// above. throwApiError already marks us unreachable and drops the Sentry
			// noise for these; short-circuiting here keeps the tailored voting empty
			// state instead of the generic error page.
			if (response && isBackendUnreachableStatus(response.status)) {
				markReachable(false);
				return { title: 'Голосование', nominations: [], offlineUnavailable: true };
			}
			throwApiError(apiError, response, 'Не удалось загрузить номинации');
		}

		return {
			title: 'Голосование',
			nominations: data?.nominations ?? [],
			offlineUnavailable: false
		};
	} catch (err) {
		// A reachable failure surfaced by throwApiError: re-throw so the error page
		// shows the mapped status. Anything else is a network failure (offline /
		// timeout) — mark us unreachable and fall to the honest online-only state.
		if (isHttpError(err)) throw err;
		markReachable(false);
		return { title: 'Голосование', nominations: [], offlineUnavailable: true };
	}
};
