import { getVotingStatusOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent }) => {
	const { queryClient } = await parent();
	void queryClient.query(getVotingStatusOptions()).catch(() => {});
};
