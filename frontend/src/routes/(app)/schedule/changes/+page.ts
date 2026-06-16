import { error, redirect } from '@sveltejs/kit';
import { createApiClient } from '$lib/api';
import { canManageSchedule } from '$lib/utils/permissions';
import { readCache, writeCache } from '$lib/utils/offlineCache';
import { timeoutSignal, FIRST_PAINT_TIMEOUT_MS } from '$lib/utils/fetchTimeout';
import { isReachable, markReachable } from '$lib/services/reachability';
import type { ScheduleChangeFullDTO } from '$lib/types/schedule';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	const { user } = await parent();

	if (!user) {
		redirect(303, '/login');
	}

	if (!canManageSchedule(user)) {
		error(403, 'У вас нет доступа к этой странице');
	}

	depends('app:schedule:changes');

	const cacheKey = `schedule-changes:${user.id}`;

	const staleFromCache = async () => {
		const cached = await readCache<ScheduleChangeFullDTO[]>(cacheKey);
		if (cached) {
			return { title: 'Изменения расписания', schedule_changes: cached, stale: true };
		}
		error(503, 'Не удалось загрузить изменения расписания');
	};

	// Known unreachable: serve the cached copy immediately, no dead network wait.
	if (!isReachable()) {
		return staleFromCache();
	}

	const client = createApiClient();

	try {
		const { data, error: fetchError } = await client.GET('/schedule/changes/', {
			fetch,
			signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
		});

		// Got an HTTP response (even an error) → the server is reachable.
		markReachable(true);

		if (fetchError || !data) {
			// Reachable but errored — prefer the cached copy over a hard failure.
			return staleFromCache();
		}

		const scheduleChanges = data.schedule_changes ?? [];
		void writeCache(cacheKey, scheduleChanges);
		return { title: 'Изменения расписания', schedule_changes: scheduleChanges, stale: false };
	} catch {
		// Network failure / timeout: serve the last synced copy.
		markReachable(false);
		return staleFromCache();
	}
};
