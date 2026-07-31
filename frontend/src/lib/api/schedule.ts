import type { createApiClient } from '$lib/api';
import type {
	ScheduleEventFullDTO,
	ScheduleEventWithSubscription,
	SubscriptionFullDTO
} from '$lib/types/schedule';

import { fetchWithCache, universalScope, userScope } from '$lib/utils/offlineCache';

/**
 * Cache and merge helpers for the schedule endpoints, shared by the home page
 * and the programme page. Both render the same rows from the same two cache
 * entries; keeping the keys and the offline contract in one place stops the two
 * pages drifting into caches that shadow each other.
 */

type ApiClient = ReturnType<typeof createApiClient>;

// Shared across every viewer: the schedule carries no per-user data, so it lives in
// the universal store — one entry serves guests and all accounts, surviving logout.
const SCHEDULE_CACHE_KEY = 'schedule';

/** Load the public schedule (universal cache). `data` is undefined on a complete miss. */
export function loadSchedule(client: ApiClient, fetch: typeof globalThis.fetch) {
	return fetchWithCache<ScheduleEventFullDTO[]>({
		key: SCHEDULE_CACHE_KEY,
		scope: universalScope,
		fetcher: async ({ signal }) => {
			const { data, error } = await client.GET('/schedule/', { fetch, signal });
			// Reachable but errored → fall back to cache.
			if (error || !data) return undefined;
			return data.schedule ?? [];
		}
	});
}

/**
 * Load the current user's subscriptions (per-user cache). Guests have none, so we
 * skip the request and return an empty list. A miss degrades to "no badges" rather
 * than failing the page — the schedule itself drives the offline empty state.
 */
export async function loadSubscriptions(
	client: ApiClient,
	fetch: typeof globalThis.fetch,
	userId: string | undefined
): Promise<SubscriptionFullDTO[]> {
	if (!userId) return [];

	const { data } = await fetchWithCache<SubscriptionFullDTO[]>({
		key: `subscriptions:${userId}`,
		scope: userScope,
		fetcher: async ({ signal }) => {
			const { data, error } = await client.GET('/schedule/subscriptions/', { fetch, signal });
			if (error || !data) return undefined;
			return data.subscriptions ?? [];
		}
	});

	return data ?? [];
}

/** Attach each event's subscription (matched by event id) to reproduce the merged row shape. */
export function mergeSubscriptions(
	schedule: ScheduleEventFullDTO[],
	subscriptions: SubscriptionFullDTO[]
): ScheduleEventWithSubscription[] {
	const byEventId = new Map(
		subscriptions.map((sub) => [sub.event.id, { id: sub.id, counter: sub.counter }])
	);

	return schedule.map((event) => ({
		...event,
		user_subscription: byEventId.get(event.id) ?? null
	}));
}
