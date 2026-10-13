import {
	getPublicConfigOptions,
	getScheduleOptions,
	getVotingStatusOptions
} from '#lib/api/generated/@tanstack/svelte-query.gen.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	// Start the fetches as early as SvelteKit preloads the route (on hover/tap);
	// the page subscribes to the same queries and renders cached copies meanwhile.
	const { queryClient } = await parent();
	void queryClient.query(getPublicConfigOptions()).catch(() => {});
	void queryClient.query(getScheduleOptions()).catch(() => {});
	void queryClient.query(getVotingStatusOptions()).catch(() => {});

	// AppNavbar renders this as the page <h1>; it matches the tab label, as on
	// every other tab.
	return { title: 'Главная' };
};
