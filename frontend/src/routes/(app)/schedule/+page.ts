import type { ScheduleEventFullDto, SubscriptionFullDto } from '$lib/api/generated';
import type { ScheduleEventWithSubscription, ScheduleView } from '$lib/types/schedule';

import { createApiClient } from '$lib/api';
import { getSchedule, getSubscriptions } from '$lib/api/generated';
import { isReachable } from '$lib/services/reachability';
import {
	type FetchWithCacheResult,
	fetchWithCacheSwr,
	type FetchWithCacheSwrResult,
	universalScope,
	userScope
} from '$lib/utils/offlineCache';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

// Shared across every viewer: the schedule carries no per-user data, so it lives in
// the universal store — one entry serves guests and all accounts, surviving logout.
const SCHEDULE_CACHE_KEY = 'schedule';

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	depends('app:schedule');

	const { user } = await parent();
	const client = createApiClient();

	// Schedule (universal) and subscriptions (per-user) come from two endpoints so
	// each caches on its own. Fetch them concurrently — total latency is the slower
	// of the two, not the sum. Guests skip the subscriptions request entirely.
	// Stale-while-revalidate: with a saved copy (the root layout warms both on first
	// boot) this resolves off IndexedDB, and the network copy follows in `revalidated`.
	const [scheduleResult, subscriptionsResult] = await Promise.all([
		fetchWithCacheSwr<ScheduleEventFullDto[]>({
			key: SCHEDULE_CACHE_KEY,
			scope: universalScope,
			fetcher: async ({ signal }) => {
				const { data, error: fetchError } = await getSchedule({ client, fetch, signal });
				// Reachable but errored → fall back to cache.
				if (fetchError || !data) return undefined;
				return data.schedule ?? [];
			}
		}),
		fetchSubscriptions(client, fetch, user?.id)
	]);

	const view = toView(scheduleResult, subscriptionsResult, scheduleResult.revalidated !== null);
	if (view === undefined) error(503, 'Не удалось загрузить программу');

	return {
		title: 'Программа',
		...view,
		revalidated: revalidateView(scheduleResult, subscriptionsResult)
	};
};

/**
 * Load the current user's subscriptions (per-user cache). Guests have none, so we
 * skip the request and return an empty list. A miss degrades to "no badges" rather
 * than failing the page — the schedule itself drives the offline empty state.
 */
async function fetchSubscriptions(
	client: ReturnType<typeof createApiClient>,
	fetch: typeof globalThis.fetch,
	userId: string | undefined
): Promise<FetchWithCacheSwrResult<SubscriptionFullDto[]>> {
	if (!userId) return { data: [], stale: false, revalidated: null };

	return fetchWithCacheSwr<SubscriptionFullDto[]>({
		key: 'subscriptions',
		scope: userScope,
		fetcher: async ({ signal }) => {
			const { data, error: fetchError } = await getSubscriptions({
				client,
				fetch,
				signal
			});
			if (fetchError || !data) return undefined;
			return data.subscriptions ?? [];
		}
	});
}

/**
 * The page once both background revalidations settle, or `null` when neither
 * entry was served from cache (the view is already the network copy).
 */
function revalidateView(
	scheduleResult: FetchWithCacheSwrResult<ScheduleEventFullDto[]>,
	subscriptionsResult: FetchWithCacheSwrResult<SubscriptionFullDto[]>
): Promise<ScheduleView | undefined> | null {
	if (!scheduleResult.revalidated && !subscriptionsResult.revalidated) return null;

	return Promise.all([
		scheduleResult.revalidated ?? scheduleResult,
		subscriptionsResult.revalidated ?? subscriptionsResult
	]).then(([schedule, subscriptions]) => toView(schedule, subscriptions, false));
}

/**
 * Merge both results into the page view. `undefined` means a reachable failure
 * with nothing cached — the caller decides whether that is a hard error.
 */
function toView(
	scheduleResult: FetchWithCacheResult<ScheduleEventFullDto[]>,
	subscriptionsResult: FetchWithCacheResult<SubscriptionFullDto[]>,
	revalidating: boolean
): ScheduleView | undefined {
	const { data: schedule, cachedAt } = scheduleResult;

	if (schedule === undefined) {
		// Offline with nothing cached: degrade to a calm inline state so the app shell
		// and bottom nav stay usable. A real online failure is still a hard error.
		if (!isReachable()) {
			return { schedule: [], stale: true, cachedAt: undefined, offlineMiss: true };
		}
		return undefined;
	}

	// A cached copy that is being revalidated is not "stale" for the notice: its
	// copy says there is no connection, which is false while the refresh runs. A
	// revalidation that fails resolves with `stale: true` and raises it then.
	const stale = scheduleResult.stale && !revalidating;

	return {
		schedule: mergeSubscriptions(schedule, subscriptionsResult.data ?? []),
		stale,
		cachedAt,
		offlineMiss: false
	};
}

/** Attach each event's subscription (matched by event id) to reproduce the merged row shape. */
function mergeSubscriptions(
	schedule: ScheduleEventFullDto[],
	subscriptions: SubscriptionFullDto[]
): ScheduleEventWithSubscription[] {
	const byEventId = new Map(
		subscriptions.map((sub) => [sub.event.id, { id: sub.id, counter: sub.counter }])
	);

	return schedule.map((event) => ({
		...event,
		user_subscription: byEventId.get(event.id) ?? null
	}));
}
