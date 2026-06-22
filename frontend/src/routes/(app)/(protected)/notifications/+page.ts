import { error } from '@sveltejs/kit';
import { createApiClient } from '$lib/api';
import { fetchWithCache, userStore } from '$lib/utils/offlineCache';
import { isReachable } from '$lib/services/reachability';
import {
	NOTIFICATION_PAGE_REQUEST_LIMIT,
	NOTIFICATION_PAGE_SIZE
} from '$lib/constants/notifications';
import type { NotificationDTO } from '$lib/types/notifications';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	depends('app:notifications');

	const { user } = await parent();
	// Per-user key: notifications are the viewer's own feed.
	const cacheKey = `notifications:${user?.id ?? 'guest'}`;

	const client = createApiClient();

	// Cache the raw first page (request limit length) so hasMore stays computable offline.
	const { data, stale, cachedAt } = await fetchWithCache<NotificationDTO[]>({
		key: cacheKey,
		store: userStore,
		fetcher: async ({ signal }) => {
			const { data, error: fetchError } = await client.GET('/notifications/', {
				fetch,
				signal,
				params: {
					query: {
						limit: NOTIFICATION_PAGE_REQUEST_LIMIT,
						offset: 0
					}
				}
			});
			// Reachable but errored → fall back to cache.
			if (fetchError || !data) return undefined;
			return data.notifications ?? [];
		}
	});

	if (data === undefined) {
		// Offline with nothing cached: degrade to a calm inline state so the app shell
		// and bottom nav stay usable. A real online failure is still a hard error.
		if (!isReachable()) {
			return {
				title: 'Уведомления',
				notifications: [],
				hasMore: false,
				stale: true,
				cachedAt: undefined,
				offlineMiss: true
			};
		}
		error(503, 'Не удалось загрузить уведомления');
	}

	return {
		title: 'Уведомления',
		notifications: data.slice(0, NOTIFICATION_PAGE_SIZE),
		hasMore: data.length > NOTIFICATION_PAGE_SIZE,
		stale,
		cachedAt,
		offlineMiss: false
	};
};
