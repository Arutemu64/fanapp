import { createApiClient } from '$lib/api';
import { getVotingStatus } from '$lib/api/generated';
import { isBackendUnreachableStatus, isReachable, markReachable } from '$lib/services/reachability';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';

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
		const { data, error, response } = await getVotingStatus({
			client,
			fetch,
			signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
		});

		if (error) {
			// The client returns a network failure (offline / timeout / abort) as an
			// error with no `response`, and a live proxy over a dead backend as a
			// gateway 5xx. Both mean unreachable: mark us so the page loads skip their
			// own doomed requests, and hide the banner without a noisy console error.
			if (!response || isBackendUnreachableStatus(response.status)) {
				markReachable(false);
				return { votingStatus: undefined };
			}
			console.error('Error fetching voting status:', error);
			return { votingStatus: undefined };
		}

		return { votingStatus: data };
	} catch {
		// Defensive: nothing above is expected to throw (the client resolves failures
		// into `error`), but an unexpected throw must not crash the voting shell.
		markReachable(false);
		return { votingStatus: undefined };
	}
};
