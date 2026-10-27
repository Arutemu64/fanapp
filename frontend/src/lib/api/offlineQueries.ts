import type { InfiniteData, QueryClient, QueryKey } from '@tanstack/svelte-query';

import {
	countUnreadNotificationsOptions,
	countUnreadNotificationsQueryKey,
	getCurrentUserQueryKey,
	getPublicConfigOptions,
	getPublicConfigQueryKey,
	getQuestOptions,
	getQuestQueryKey,
	getScheduleOptions,
	getScheduleQueryKey,
	listQuestHistoryInfiniteOptions,
	listQuestHistoryQueryKey,
	listSubscriptionsOptions,
	listSubscriptionsQueryKey,
	listUserNotificationsInfiniteOptions,
	listUserNotificationsQueryKey
} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { NOTIFICATION_PAGE_SIZE } from '#lib/constants/notifications.js';
import { currentUserOptions } from '#lib/services/identity.js';
import { isReachable } from '#lib/services/reachability.js';

export const OFFLINE_QUERY_KEYS = [
	getCurrentUserQueryKey(),
	getPublicConfigQueryKey(),
	getScheduleQueryKey(),
	listSubscriptionsQueryKey(),
	listUserNotificationsQueryKey(),
	countUnreadNotificationsQueryKey(),
	getQuestQueryKey(),
	listQuestHistoryQueryKey()
];

const OFFLINE_QUERY_IDS = new Set(OFFLINE_QUERY_KEYS.map(([{ _id }]) => _id));

export function isOfflineQuery(queryKey: QueryKey): boolean {
	const [{ _id }] = queryKey as [{ _id: string }];
	return OFFLINE_QUERY_IDS.has(_id);
}

export const CACHE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;

export const QUERY_CACHE_BUSTER = '9';

const QUEST_HISTORY_PAGE_SIZE = 20;

type FeedData = InfiniteData<unknown>;

export function notificationsFeedOptions() {
	return {
		...listUserNotificationsInfiniteOptions({ query: { limit: NOTIFICATION_PAGE_SIZE } }),
		initialPageParam: {},
		getNextPageParam: (lastPage: { next_cursor?: string | null }) =>
			lastPage.next_cursor ?? undefined
	};
}

export function questHistoryFeedOptions() {
	return {
		...listQuestHistoryInfiniteOptions({ query: { limit: QUEST_HISTORY_PAGE_SIZE } }),
		initialPageParam: {},
		getNextPageParam: (lastPage: { next_cursor?: string | null }) =>
			lastPage.next_cursor ?? undefined
	};
}

function trimOffScreenFeed(queryClient: QueryClient, queryKey: QueryKey): boolean {
	const query = queryClient.getQueryCache().find<FeedData>({ queryKey, exact: true });
	if (!query || query.getObserversCount() > 0) return false;

	const { staleTime = 0 } = queryClient.defaultQueryOptions({ queryKey });
	if (typeof staleTime !== 'number' || !query.isStaleByTime(staleTime)) return false;

	queryClient.setQueryData<FeedData>(
		queryKey,
		(feed) => feed && { pages: feed.pages.slice(0, 1), pageParams: feed.pageParams.slice(0, 1) },
		{ updatedAt: query.state.dataUpdatedAt }
	);
	return true;
}

export async function warmOfflineCache(queryClient: QueryClient): Promise<void> {
	if (!isReachable()) return;

	const configFetch = queryClient.query(getPublicConfigOptions()).catch(() => undefined);
	void queryClient.query(getScheduleOptions()).catch(() => {});

	const user = queryClient.getQueryData(currentUserOptions().queryKey);
	if (!user) return;

	void queryClient.query(listSubscriptionsOptions()).catch(() => {});
	void queryClient.query(countUnreadNotificationsOptions()).catch(() => {});
	const notificationsFeed = notificationsFeedOptions();
	const notificationsTrimmed = trimOffScreenFeed(queryClient, notificationsFeed.queryKey);
	void queryClient
		.infiniteQuery(
			notificationsTrimmed ? { ...notificationsFeed, staleTime: 0 } : notificationsFeed
		)
		.catch(() => {});

	const config = await configFetch;
	const stillSignedIn = queryClient.getQueryData(currentUserOptions().queryKey);
	if (config?.quest_enabled && stillSignedIn) {
		void queryClient.query(getQuestOptions()).catch(() => {});
		const questHistoryFeed = questHistoryFeedOptions();
		const questHistoryTrimmed = trimOffScreenFeed(queryClient, questHistoryFeed.queryKey);
		void queryClient
			.infiniteQuery(questHistoryTrimmed ? { ...questHistoryFeed, staleTime: 0 } : questHistoryFeed)
			.catch(() => {});
	}
}
