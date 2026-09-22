import { listVotingNominationsOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';

import type { PageLoad } from './$types';

// Voting is a live, online-only surface: casting a vote is a mutation, and the
// open/closed and already-voted state must never be shown stale (a cached ballot
// you can't submit is a dead end). `gcTime: 0` keeps it out of the persisted
// cache, so an offline visit finds nothing and the page shows an honest
// "online only" state rather than a stale ballot.
export const load: PageLoad = async ({ parent }) => {
	const { queryClient } = await parent();

	void queryClient.prefetchQuery({ ...listVotingNominationsOptions(), gcTime: 0 });

	return { title: 'Голосование' };
};
