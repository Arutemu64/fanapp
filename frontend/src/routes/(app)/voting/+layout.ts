import { fetchVotingStatus } from '#lib/utils/votingStatus.js';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ fetch, depends }) => {
	// Voting availability derives from the configured [start, end) range, so the
	// status banner must refresh when organizers change it. Tie this read to the
	// same 'app:config' key the home page uses; +layout.svelte re-invalidates it on
	// a config_updated SSE event (and on reconnect, to self-heal a missed one).
	depends('app:config');

	// The status banner simply hides on an undefined status (offline or failed).
	return { votingStatus: await fetchVotingStatus(fetch) };
};
