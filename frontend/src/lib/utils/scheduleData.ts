import type { ScheduleEventFullDto, SubscriptionFullDto } from '#lib/api/generated/index.js';
import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

import { getSchedule, getSubscriptions } from '#lib/api/generated/index.js';
import { createApiClient } from '#lib/api/index.js';
import { fetchWithCache, universalScope, userScope } from '#lib/utils/offlineCache.js';

// Shared across every viewer: the schedule carries no per-user data, so it lives in
// the universal store — one entry serves guests and all accounts, surviving logout.
export const SCHEDULE_CACHE_KEY = 'schedule';
export const SUBSCRIPTIONS_CACHE_KEY = 'subscriptions';

interface ScheduleLoadResult {
	/** Undefined on a complete miss: unreachable or failed, with nothing cached. */
	schedule: ScheduleEventWithSubscription[] | undefined;
	stale: boolean;
	cachedAt: number | undefined;
}

/**
 * Load the schedule merged with the viewer's subscriptions, each from its own
 * offline cache. Read by the schedule page and the home "now on stage" card, so
 * both stay on one cache entry and one row shape.
 */
export async function loadScheduleWithSubscriptions(
	fetch: typeof globalThis.fetch,
	userId: string | undefined
): Promise<ScheduleLoadResult> {
	const client = createApiClient();

	// Schedule (universal) and subscriptions (per-user) come from two endpoints so
	// each caches on its own. Fetch them concurrently — total latency is the slower
	// of the two, not the sum. Guests skip the subscriptions request entirely.
	const [scheduleResult, subscriptions] = await Promise.all([
		fetchWithCache<ScheduleEventFullDto[]>({
			key: SCHEDULE_CACHE_KEY,
			scope: universalScope,
			fetcher: async ({ signal }) => {
				const { data, error: fetchError } = await getSchedule({ client, fetch, signal });
				// Reachable but errored → fall back to cache.
				if (fetchError || !data) return undefined;
				return data.schedule ?? [];
			}
		}),
		fetchSubscriptions(client, fetch, userId)
	]);

	const { data: schedule, stale, cachedAt } = scheduleResult;

	return {
		schedule: schedule === undefined ? undefined : mergeSubscriptions(schedule, subscriptions),
		stale,
		cachedAt
	};
}

/**
 * Load the current user's subscriptions (per-user cache). Guests have none, so we
 * skip the request and return an empty list. A miss degrades to "no badges" rather
 * than failing the page — the schedule itself drives the offline empty state.
 */
async function fetchSubscriptions(
	client: ReturnType<typeof createApiClient>,
	fetch: typeof globalThis.fetch,
	userId: string | undefined
): Promise<SubscriptionFullDto[]> {
	if (!userId) return [];

	const { data } = await fetchWithCache<SubscriptionFullDto[]>({
		key: SUBSCRIPTIONS_CACHE_KEY,
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

	return data ?? [];
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
