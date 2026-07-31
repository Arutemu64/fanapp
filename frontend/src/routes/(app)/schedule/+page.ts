import type {
	ScheduleEventFullDTO,
	ScheduleEventWithSubscription,
	SubscriptionFullDTO
} from '$lib/types/schedule';

import { createApiClient } from '$lib/api';
import { isReachable } from '$lib/services/reachability';
import { fetchWithCache, universalScope, userScope } from '$lib/utils/offlineCache';
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
	// Captured from the response rather than cached: it describes this fetch, not
	// the schedule. Stays 0 on a cache hit, which is the honest answer — we have
	// no reading of the server clock from an offline render.
	let serverClockOffsetMs = 0;

	const [scheduleResult, subscriptions] = await Promise.all([
		fetchWithCache<CachedSchedule>({
			key: SCHEDULE_CACHE_KEY,
			scope: universalScope,
			fetcher: async ({ signal }) => {
				const {
					data,
					error: fetchError,
					response
				} = await client.GET('/schedule/', { fetch, signal });
				// Reachable but errored → fall back to cache.
				if (fetchError || !data) return undefined;
				serverClockOffsetMs = readServerClockOffset(response);
				return {
					schedule: data.schedule ?? [],
					transitionBufferSeconds: data.transition_buffer_seconds
				};
			}
		}),
		fetchSubscriptions(client, fetch, user?.id)
	]);

	const { data: cached, stale, cachedAt } = scheduleResult;

	if (cached === undefined) {
		// Offline with nothing cached: degrade to a calm inline state so the app shell
		// and bottom nav stay usable. A real online failure is still a hard error.
		if (!isReachable()) {
			return {
				title: 'Программа',
				schedule: [],
				transitionBufferSeconds: null,
				serverClockOffsetMs: 0,
				stale: true,
				cachedAt: undefined,
				offlineMiss: true
			};
		}
		error(503, 'Не удалось загрузить программу');
	}

	const { schedule, transitionBufferSeconds } = normalizeCached(cached);

	return {
		title: 'Программа',
		schedule: mergeSubscriptions(schedule, subscriptions),
		transitionBufferSeconds,
		serverClockOffsetMs,
		stale,
		cachedAt,
		offlineMiss: false
	};
};

/**
 * How far the server clock is ahead of this device's, in milliseconds, read from
 * the `Date` header every response carries (RFC 9110 §6.6.1). A phone with a
 * badly set clock would otherwise skew every countdown on the schedule screen.
 *
 * Readable because the app and the API are same-origin behind Caddy — `Date` is
 * not CORS-safelisted, so a split-origin deployment would have to add it to
 * `Access-Control-Expose-Headers` for this to keep working.
 */
function readServerClockOffset(response: Response): number {
	const header = response.headers.get('Date');
	if (!header) return 0;

	const serverMs = Date.parse(header);
	if (Number.isNaN(serverMs)) return 0;

	return serverMs - Date.now();
}

/** What this page persists: the events plus the one setting the projection needs. */
interface CachedSchedule {
	schedule: ScheduleEventFullDTO[];
	transitionBufferSeconds: number;
}

/**
 * Entries cached before the buffer was persisted are a bare event array. Report
 * a null buffer for those rather than inventing a fallback value that would
 * silently disagree with the server's — the page then falls back to the
 * `expected_start_time` the rows already carry.
 */
function normalizeCached(cached: CachedSchedule | ScheduleEventFullDTO[]): {
	schedule: ScheduleEventFullDTO[];
	transitionBufferSeconds: number | null;
} {
	if (Array.isArray(cached)) {
		return { schedule: cached, transitionBufferSeconds: null };
	}
	return { schedule: cached.schedule, transitionBufferSeconds: cached.transitionBufferSeconds };
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
): Promise<SubscriptionFullDTO[]> {
	if (!userId) return [];

	const { data } = await fetchWithCache<SubscriptionFullDTO[]>({
		key: `subscriptions:${userId}`,
		scope: userScope,
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
