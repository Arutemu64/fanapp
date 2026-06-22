import { error } from '@sveltejs/kit';
import { createApiClient } from '$lib/api';
import { fetchWithCache, universalStore, userStore } from '$lib/utils/offlineCache';
import { isReachable } from '$lib/services/reachability';
import type {
	ScheduleEventFullDTO,
	ScheduleEventWithSubscription,
	SubscriptionFullDTO
} from '$lib/types/schedule';
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
	const [scheduleResult, subscriptions] = await Promise.all([
		fetchWithCache<ScheduleEventFullDTO[]>({
			key: SCHEDULE_CACHE_KEY,
			store: universalStore,
			fetcher: async ({ signal }) => {
				const { data, error: fetchError } = await client.GET('/schedule/', { fetch, signal });
				// Reachable but errored → fall back to cache.
				if (fetchError || !data) return undefined;
				return data.schedule ?? [];
			}
		}),
		fetchSubscriptions(client, fetch, user?.id)
	]);

	const { data: schedule, stale, cachedAt } = scheduleResult;

	if (schedule === undefined) {
		// Offline with nothing cached: degrade to a calm inline state so the app shell
		// and bottom nav stay usable. A real online failure is still a hard error.
		if (!isReachable()) {
			return {
				title: 'Расписание',
				schedule: [],
				stale: true,
				cachedAt: undefined,
				offlineMiss: true
			};
		}
		error(503, 'Не удалось загрузить расписание');
	}

	return {
		title: 'Расписание',
		schedule: mergeSubscriptions(schedule, subscriptions),
		stale,
		cachedAt,
		offlineMiss: false
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
): Promise<SubscriptionFullDTO[]> {
	if (!userId) return [];

	const { data } = await fetchWithCache<SubscriptionFullDTO[]>({
		key: `subscriptions:${userId}`,
		store: userStore,
		fetcher: async ({ signal }) => {
			const { data, error: fetchError } = await client.GET('/schedule/subscriptions/', {
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
