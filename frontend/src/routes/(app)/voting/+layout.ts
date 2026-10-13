import { getVotingStatusOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent }) => {
	// Start the fetch as early as SvelteKit preloads the route (on hover/tap); the
	// pages subscribe to the same query.
	const { queryClient } = await parent();
	void queryClient.query(getVotingStatusOptions()).catch(() => {});
};
