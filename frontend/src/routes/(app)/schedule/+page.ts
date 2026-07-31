import { createApiClient } from '$lib/api';
import { loadSchedule, loadSubscriptions, mergeSubscriptions } from '$lib/api/schedule';
import { isReachable } from '$lib/services/reachability';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	depends('app:schedule');

	const { user } = await parent();
	const client = createApiClient();

	// Schedule (universal) and subscriptions (per-user) come from two endpoints so
	// each caches on its own. Fetch them concurrently — total latency is the slower
	// of the two, not the sum. Guests skip the subscriptions request entirely.
	const [scheduleResult, subscriptions] = await Promise.all([
		loadSchedule(client, fetch),
		loadSubscriptions(client, fetch, user?.id)
	]);

	const { data: schedule, stale, cachedAt } = scheduleResult;

	if (schedule === undefined) {
		// Offline with nothing cached: degrade to a calm inline state so the app shell
		// and bottom nav stay usable. A real online failure is still a hard error.
		if (!isReachable()) {
			return {
				title: 'Программа',
				schedule: [],
				stale: true,
				cachedAt: undefined,
				offlineMiss: true
			};
		}
		error(503, 'Не удалось загрузить программу');
	}

	return {
		title: 'Программа',
		schedule: mergeSubscriptions(schedule, subscriptions),
		stale,
		cachedAt,
		offlineMiss: false
	};
};
