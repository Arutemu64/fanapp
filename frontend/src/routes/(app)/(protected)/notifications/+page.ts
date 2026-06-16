import { error } from '@sveltejs/kit';
import { createApiClient } from '$lib/api';
import { fetchWithCache } from '$lib/utils/offlineCache';
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
	const { data, stale } = await fetchWithCache<NotificationDTO[]>({
		key: cacheKey,
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

	// Complete miss (errored/offline with nothing cached): hard failure.
	if (data === undefined) {
		error(503, 'Не удалось загрузить уведомления');
	}

	return {
		title: 'Уведомления',
		notifications: data.slice(0, NOTIFICATION_PAGE_SIZE),
		hasMore: data.length > NOTIFICATION_PAGE_SIZE,
		stale
	};
};
