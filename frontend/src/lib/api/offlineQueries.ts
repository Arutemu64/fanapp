import type { QueryClient, QueryKey } from '@tanstack/svelte-query';

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
	getSubscriptionsOptions,
	getSubscriptionsQueryKey,
	listQuestHistoryInfiniteOptions,
	listQuestHistoryQueryKey,
	listUserNotificationsInfiniteOptions,
	listUserNotificationsQueryKey
} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { NOTIFICATION_PAGE_SIZE } from '#lib/constants/notifications.js';
import { currentUserOptions } from '#lib/services/identity.js';
import { isReachable } from '#lib/services/reachability.js';

// The screens that must open offline: the identity the guards and the profile
// read, the home hero, the programme with the viewer's subscriptions, the
// notifications with their badge, the quest score and standings (shown with
// their sync time, since ranks move during the festival) and the player's award
// history. Only these are written to IndexedDB. Every other query is online-only:
// fetched fresh after a cold start and dropped from memory five minutes after
// its screen closes (TanStack's default gcTime) — voting must not show a stale
// ballot, and the organizer tools hold other people's details that have no
// business on the device.
export const OFFLINE_QUERY_KEYS = [
	getCurrentUserQueryKey(),
	getPublicConfigQueryKey(),
	getScheduleQueryKey(),
	getSubscriptionsQueryKey(),
	listUserNotificationsQueryKey(),
	countUnreadNotificationsQueryKey(),
	getQuestQueryKey(),
	listQuestHistoryQueryKey()
];

// Matched by operation id, the first part of every hey-api query key, so a
// list key also covers its paginated variant.
const OFFLINE_QUERY_IDS = new Set(OFFLINE_QUERY_KEYS.map(([{ _id }]) => _id));

export function isOfflineQuery(queryKey: QueryKey): boolean {
	const [{ _id }] = queryKey as [{ _id: string }];
	return OFFLINE_QUERY_IDS.has(_id);
}

// How long a cached copy may serve the app offline: a festival weekend plus the
// trip there and back, where the persister's 24h default would drop the
// programme for anyone who didn't open the app for a day. StaleDataNotice shows
// how old what's on screen is. The offline queries keep this gcTime too, or they
// are garbage-collected before they are ever persisted:
// https://tanstack.com/query/latest/docs/framework/react/plugins/persistQueryClient
export const CACHE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;

const QUEST_HISTORY_PAGE_SIZE = 20;

// The two feeds are infinite queries, so the key carries the page size: the warm
// prefetch below and the feed on screen must build the same options, or the
// prefetch fills an entry the screen never reads.

export function notificationsFeedOptions() {
	return {
		...listUserNotificationsInfiniteOptions({ query: { limit: NOTIFICATION_PAGE_SIZE } }),
		// An object page param is request overrides to hey-api, a string the cursor:
		// an empty object asks for the first page.
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

/**
 * Fetch every offline screen's data the viewer can see, so it is saved before
 * the network goes — not only the screens they happened to open. Mobile
 * shutdowns leave attendees hopping between Wi-Fi spots, so this runs whenever
 * a window opens: at boot and login, on the offline→online edge and on return
 * to the app. A query fetched within its staleTime is skipped, and the schedule
 * revalidates with its ETag, so a repeat costs a few cheap requests. Offline it
 * does nothing, and a failed fetch leaves the saved copy as it was: the next
 * window tries again.
 */
export function warmOfflineCache(queryClient: QueryClient): void {
	if (!isReachable()) return;

	void queryClient.query(getPublicConfigOptions()).catch(() => {});
	void queryClient.query(getScheduleOptions()).catch(() => {});

	const user = queryClient.getQueryData(currentUserOptions().queryKey);
	if (!user) return;

	void queryClient.query(getSubscriptionsOptions()).catch(() => {});
	void queryClient.query(countUnreadNotificationsOptions()).catch(() => {});
	void queryClient.infiniteQuery(notificationsFeedOptions()).catch(() => {});

	const config = queryClient.getQueryData(getPublicConfigOptions().queryKey);
	if (config?.quest_enabled) {
		void queryClient.query(getQuestOptions()).catch(() => {});
		void queryClient.infiniteQuery(questHistoryFeedOptions()).catch(() => {});
	}
}
