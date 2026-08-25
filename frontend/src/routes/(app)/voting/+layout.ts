import { createApiClient } from '$lib/api';
import { isReachable } from '$lib/services/reachability';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ fetch }) => {
	// Voting status is a live, online-only read like the nominations it frames (see
	// ./+page.ts). When the backend is known unreachable, skip the doomed request;
	// the status banner simply hides on an undefined status.
	if (!isReachable()) {
		return { votingStatus: undefined };
	}

	const client = createApiClient();

	try {
		const { data, error } = await client.GET('/voting/status', { fetch });

		if (error) {
			console.error('Error fetching voting status:', error);
			return { votingStatus: undefined };
		}

		return { votingStatus: data };
	} catch {
		// A network failure (offline / timeout) is thrown by fetch, not returned as
		// `error`. The client middleware marks us unreachable so the page loads
		// skip their own doomed requests; hide the banner instead of crashing the
		// whole load.
		return { votingStatus: undefined };
	}
};
