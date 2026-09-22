import {
	getScheduleOptions,
	getSubscriptionsOptions
} from '$lib/api/generated/@tanstack/svelte-query.gen';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	// Schedule and subscriptions come from two endpoints so each caches, persists
	// and invalidates on its own. Prefetched concurrently — total latency is the
	// slower of the two, not the sum. Guests have no subscriptions, so they skip
	// that request entirely.
	await Promise.all([
		queryClient.prefetchQuery(getScheduleOptions()),
		user ? queryClient.prefetchQuery(getSubscriptionsOptions()) : Promise.resolve()
	]);

	return { title: 'Программа' };
};
