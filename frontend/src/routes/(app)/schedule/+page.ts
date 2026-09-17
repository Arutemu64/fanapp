import { getScheduleQueryKey } from '$lib/api/generated/@tanstack/svelte-query.gen';
import { scheduleQueryOptions, subscriptionsQueryOptions } from '$lib/api/queries';
import { isReachable } from '$lib/services/reachability';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

/**
 * Prefetch into the shared query cache and decide the hard-failure case. The page
 * component reads the same cache entries through `createQuery`, so invalidation
 * and background refetches drive the UI from here on — this load only has to
 * settle the question a component cannot answer: whether to render at all.
 */
export const load: PageLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	// Programme (universal) and subscriptions (per-user) are two endpoints so each
	// caches on its own. Warm them concurrently — total latency is the slower of the
	// two, not the sum. Guests have no subscriptions, so they skip that request.
	// Settled, not awaited for success: a missing subscription list degrades to "no
	// badges", and the programme's own absence is what decides the page below.
	await Promise.allSettled([
		queryClient.ensureQueryData(scheduleQueryOptions()),
		user ? queryClient.ensureQueryData(subscriptionsQueryOptions()) : Promise.resolve(undefined)
	]);

	// Nothing cached and nothing fetched. Offline that is expected — degrade to a
	// calm inline state so the app shell and bottom nav stay usable. Online it is a
	// real failure and still deserves the error page.
	if (queryClient.getQueryData(getScheduleQueryKey()) === undefined && isReachable()) {
		error(503, 'Не удалось загрузить программу');
	}

	return { title: 'Программа' };
};
