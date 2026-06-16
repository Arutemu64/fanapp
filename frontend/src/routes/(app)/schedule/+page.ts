import { error } from '@sveltejs/kit';
import { createApiClient } from '$lib/api';
import { readCache, writeCache } from '$lib/utils/offlineCache';
import { timeoutSignal, FIRST_PAINT_TIMEOUT_MS } from '$lib/utils/fetchTimeout';
import { isReachable, markReachable } from '$lib/services/reachability';
import type { ScheduleEventFullDTO } from '$lib/types/schedule';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	depends('app:schedule');

	const { user } = await parent();
	// Per-user key: the schedule carries the viewer's own subscriptions.
	const cacheKey = `schedule:${user?.id ?? 'guest'}`;

	const staleFromCache = async () => {
		const cached = await readCache<ScheduleEventFullDTO[]>(cacheKey);
		if (cached) {
			return { title: 'Расписание', schedule: cached, stale: true };
		}
		error(503, 'Не удалось загрузить расписание');
	};

	// Known unreachable: serve the cached schedule immediately, no dead network wait.
	if (!isReachable()) {
		return staleFromCache();
	}

	const client = createApiClient();

	try {
		const { data, error: fetchError } = await client.GET('/schedule/', {
			fetch,
			signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
		});

		// Got an HTTP response (even an error) → the server is reachable.
		markReachable(true);

		if (fetchError || !data) {
			// Reachable but errored — prefer the cached copy over a hard failure.
			return staleFromCache();
		}

		const schedule = data.schedule ?? [];
		// Persist the fresh copy so we can serve it next time the network is down.
		void writeCache(cacheKey, schedule);
		return { title: 'Расписание', schedule, stale: false };
	} catch {
		// Network failure / timeout: serve the last synced copy.
		markReachable(false);
		return staleFromCache();
	}
};
