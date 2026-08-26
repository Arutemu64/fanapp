import { createApiClient } from '$lib/api';
import { isReachable, markReachable } from '$lib/services/reachability';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ fetch, depends }) => {
	// Voting availability now derives from the configured [start, end) range, so the
	// status banner must refresh when organizers change it. Tie this read to the
	// same 'app:config' key the home hero uses; +layout.svelte re-invalidates it on
	// a config_updated SSE event (and on reconnect, to self-heal a missed one).
	depends('app:config');

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
		// `error`. Mark us unreachable so the page loads skip their own doomed
		// requests, and hide the banner instead of crashing the whole load.
		markReachable(false);
		return { votingStatus: undefined };
	}
};
