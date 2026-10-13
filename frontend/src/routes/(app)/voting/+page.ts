import { listVotingNominationsOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	// Start the fetch as early as SvelteKit preloads the route (on hover/tap); the
	// page subscribes to the same query.
	const { queryClient } = await parent();
	void queryClient.query(listVotingNominationsOptions()).catch(() => {});

	return { title: 'Голосование' };
};
