import { error } from '@sveltejs/kit';
import { createApiClient } from '$lib/api';
import { fetchWithCache } from '$lib/utils/offlineCache';
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

	// Complete miss (errored/offline with nothing cached): hard failure.
	if (data === undefined) {
		error(503, 'Не удалось загрузить расписание');
	}

	return { title: 'Расписание', schedule: data, stale, cachedAt };
};
