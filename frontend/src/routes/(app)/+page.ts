import { getPublicConfigOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';

import type { PageLoad } from './$types';

// Public config drives the hero's phase (before/during/after) and countdown, so it
// must render for guests and offline. Prefetched here so first paint has it, then
// read from the cache by the page. `prefetchQuery` never throws: a complete miss
// (first-ever visit made offline) leaves the query empty and the page falls back
// to the shipped defaults, while any live response wins over both.
export const load: PageLoad = async ({ parent }) => {
	const { queryClient } = await parent();

	await queryClient.prefetchQuery(getPublicConfigOptions());
};
