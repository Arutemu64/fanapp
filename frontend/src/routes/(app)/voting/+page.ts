import { listVotingNominationsOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient } = await parent();
	void queryClient.query(listVotingNominationsOptions()).catch(() => {});

	return { title: m.nav_voting() };
};
