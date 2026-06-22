import { error } from '@sveltejs/kit';
import { createApiClient } from '$lib/api';
import { fetchWithCache } from '$lib/utils/offlineCache';
import { isReachable } from '$lib/services/reachability';
import type { ScheduleEventFullDTO } from '$lib/types/schedule';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	depends('app:schedule');

	const { user } = await parent();
	// Per-user key: the schedule carries the viewer's own subscriptions.
	const cacheKey = `schedule:${user?.id ?? 'guest'}`;

	const client = createApiClient();

	const { data, stale, cachedAt } = await fetchWithCache<ScheduleEventFullDTO[]>({
		key: cacheKey,
		fetcher: async ({ signal }) => {
			const { data, error: fetchError } = await client.GET('/schedule/', { fetch, signal });
			// Reachable but errored → fall back to cache.
			if (fetchError || !data) return undefined;
			return data.schedule ?? [];
		}
	});

	if (data === undefined) {
		// Offline with nothing cached: degrade to a calm inline state so the app shell
		// and bottom nav stay usable. A real online failure is still a hard error.
		if (!isReachable()) {
			return {
				title: 'Расписание',
				schedule: [],
				stale: true,
				cachedAt: undefined,
				offlineMiss: true
			};
		}
		error(503, 'Не удалось загрузить расписание');
	}

	return { title: 'Расписание', schedule: data, stale, cachedAt, offlineMiss: false };
};
