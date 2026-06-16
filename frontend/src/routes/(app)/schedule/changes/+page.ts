import { error, redirect } from '@sveltejs/kit';
import { createApiClient } from '$lib/api';
import { canManageSchedule } from '$lib/utils/permissions';
import { fetchWithCache } from '$lib/utils/offlineCache';
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

	const client = createApiClient();

	const { data, stale } = await fetchWithCache<ScheduleChangeFullDTO[]>({
		key: cacheKey,
		fetcher: async ({ signal }) => {
			const { data, error: fetchError } = await client.GET('/schedule/changes/', { fetch, signal });
			// Reachable but errored → fall back to cache.
			if (fetchError || !data) return undefined;
			return data.schedule_changes ?? [];
		}
	});

	// Complete miss (errored/offline with nothing cached): hard failure.
	if (data === undefined) {
		error(503, 'Не удалось загрузить изменения расписания');
	}

	return { title: 'Изменения расписания', schedule_changes: data, stale };
};
