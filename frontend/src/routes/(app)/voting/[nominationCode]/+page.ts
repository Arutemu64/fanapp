import { getVotingNominationOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';

import type { PageLoad } from './$types';

// Online-only like the nominations list (see ../+page.ts): voting is a live
// mutation surface, so `gcTime: 0` keeps this ballot out of the persisted cache
// and an offline visit gets the honest "online only" state, never a stale ballot.
export const load: PageLoad = async ({ params, parent }) => {
	const { queryClient } = await parent();

	void queryClient.prefetchQuery({
		...getVotingNominationOptions({ path: { nomination_code: params.nominationCode } }),
		gcTime: 0
	});

	return { title: 'Голосование' };
};
