import { browser } from '$app/environment';
import { createApiClient } from '$lib/api';
import {
	clearUserCache,
	fetchWithCache,
	universalStore,
	userStore,
	warmCache
} from '$lib/utils/offlineCache';
import type { CurrentUserDTO } from '$lib/types/user';
import type { ScheduleEventFullDTO, SubscriptionFullDTO } from '$lib/types/schedule';
import type { LayoutLoad } from './$types';

// SPA-only: render entirely on the client. No SSR, no server load.
export const ssr = false;

// Single current-session user; cached so the app can still boot offline.
const USER_CACHE_KEY = 'me:user';

export const load: LayoutLoad = async ({ fetch, depends }) => {
	depends('app:current-user');

	const client = createApiClient();

	// `null` is a real cached value (logged out); `undefined` means "reachable but
	// no verdict, keep the cached user" (see fetcher below), so the type spans both.
	const { data } = await fetchWithCache<CurrentUserDTO | null>({
		key: USER_CACHE_KEY,
		store: userStore,
		fetcher: async ({ signal }) => {
			const { data, response, error } = await client.GET('/me/', { fetch, signal });

			// Authoritative "session ended": cache logged-out AND drop per-user caches
			// so no orphaned entries linger for the next account on a shared device.
			// Universal caches (e.g. schedule) are kept warm. Mirrors explicit logout
			// (AppNavbar.handleLogout).
			if (response.status === 401 || response.status === 403) {
				void clearUserCache();
				return null;
			}

			// Reachable but not an auth verdict (5xx / parse error / empty body): do NOT
			// downgrade identity. Returning `undefined` keeps the last-good cached user
			// instead of overwriting it with `null` — a transient error must not flip a
			// logged-in user to guest (which would orphan their per-user caches).
			if (error || !data) {
				return undefined;
			}

			return data;
		}
	});

	// A complete cache miss (offline first boot) is also "not logged in".
	const user = data ?? null;

	// Warm the offline caches on the first online boot so they're viewable even if
	// the user never opens the schedule page. Fire-and-forget: each is a no-op when
	// offline or already cached, so it never blocks first paint or refetches once
	// warmed (the schedule page's own load + SSE keep them fresh after that). Uses
	// the same keys the schedule page reads, and its own client so it isn't tied to
	// this load's tracked `fetch`.
	if (browser) {
		// Schedule is universal — one shared key for guests and every account.
		void warmCache<ScheduleEventFullDTO[]>({
			key: 'schedule',
			store: universalStore,
			fetcher: async ({ signal }) => {
				const warmClient = createApiClient();
				const { data: schedule, error } = await warmClient.GET('/schedule/', { signal });
				if (error || !schedule) return undefined;
				return schedule.schedule ?? [];
			}
		});

		// Subscriptions are per-user; only logged-in users have them.
		if (user) {
			void warmCache<SubscriptionFullDTO[]>({
				key: `subscriptions:${user.id}`,
				store: userStore,
				fetcher: async ({ signal }) => {
					const warmClient = createApiClient();
					const { data, error } = await warmClient.GET('/schedule/subscriptions/', { signal });
					if (error || !data) return undefined;
					return data.subscriptions ?? [];
				}
			});
		}
	}

	return { user };
};
