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

/**
 * The persisted cache's `buster`: a saved cache with a different value is
 * discarded whole on restore, queued writes included. Bump it (any new string)
 * in the same change as a breaking change to what is saved — a persisted
 * query's response or a queued write's request losing, renaming or retyping a
 * field, or gaining one the frontend now relies on — so no build reads a body
 * its types don't describe (docs/offline.md "Cache buster"). Hand-bumped rather
 * than the build version: every deploy would then wipe the saved programme, and
 * one applied just before a mobile shutdown would leave nothing offline.
 */
export const QUERY_CACHE_BUSTER = '4';

const QUEST_HISTORY_PAGE_SIZE = 20;

type FeedData = InfiniteData<unknown>;

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
 * A stale infinite query refetches every page it holds, one request after the
 * other (https://tanstack.com/query/latest/docs/framework/react/guides/infinite-queries),
 * so a feed scrolled ten pages deep would cost ten round trips on each warm.
 * Off screen nobody reads the older pages, so a stale feed is cut to its first
 * page, which the warm then refetches alone; the saved copy drops the rest too,
 * and the feed loads them again on scroll. On screen it is left whole, for the
 * feed's own refetch of every page it shows.
 *
 * Cut in the cache before the fetch, not by fetching `pages: 1`: a reader who
 * opens the feed mid-fetch joins the request in flight, and one returning fewer
 * pages than they were shown would shorten the list under them.
 *
 * Returns whether it cut the feed. The write clears the stale flag, so the
 * caller then forces the refetch.
 */
function trimOffScreenFeed(queryClient: QueryClient, queryKey: QueryKey): boolean {
	const query = queryClient.getQueryCache().find<FeedData>({ queryKey, exact: true });
	if (!query || query.getObserversCount() > 0) return false;

	// Unset means TanStack's own default, 0. A function or 'static' staleTime is
	// not resolved here, so a feed given one is left whole.
	const { staleTime = 0 } = queryClient.defaultQueryOptions({ queryKey });
	if (typeof staleTime !== 'number' || !query.isStaleByTime(staleTime)) return false;

	// The old timestamp stays: a first page cut from an old copy is no fresher.
	queryClient.setQueryData<FeedData>(
		queryKey,
		(feed) => feed && { pages: feed.pages.slice(0, 1), pageParams: feed.pageParams.slice(0, 1) },
		{ updatedAt: query.state.dataUpdatedAt }
	);
	return true;
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
export async function warmOfflineCache(queryClient: QueryClient): Promise<void> {
	if (!isReachable()) return;

	const configFetch = queryClient.query(getPublicConfigOptions()).catch(() => undefined);
	void queryClient.query(getScheduleOptions()).catch(() => {});

	const user = queryClient.getQueryData(currentUserOptions().queryKey);
	if (!user) return;

	void queryClient.query(getSubscriptionsOptions()).catch(() => {});
	void queryClient.query(countUnreadNotificationsOptions()).catch(() => {});
	const notificationsFeed = notificationsFeedOptions();
	const notificationsTrimmed = trimOffScreenFeed(queryClient, notificationsFeed.queryKey);
	void queryClient
		.infiniteQuery(
			notificationsTrimmed ? { ...notificationsFeed, staleTime: 0 } : notificationsFeed
		)
		.catch(() => {});

	// Awaited, not read from the cache: on a first launch nothing is saved yet,
	// and the quest data would be skipped even with the quest on. The user is
	// read again, since a logout can land while the config is on its way.
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
