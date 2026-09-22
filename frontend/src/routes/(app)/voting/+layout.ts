import { getVotingStatusOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent }) => {
	const { queryClient } = await parent();

	// Voting availability derives from the configured [start, end) range, so the
	// status banner must refresh when organizers change it: +layout.svelte
	// invalidates this query on a config_updated SSE event (and on reconnect, to
	// self-heal a missed one).
	//
	// Fire-and-forget: the banner simply hides until the status resolves, so
	// waiting on it would delay the nominations below it for nothing.
	void queryClient.prefetchQuery(getVotingStatusOptions());
};
