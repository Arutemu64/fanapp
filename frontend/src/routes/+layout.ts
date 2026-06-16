import { createApiClient } from '$lib/api';
import { fetchWithCache } from '$lib/utils/offlineCache';
import type { CurrentUserDTO } from '$lib/types/user';
import type { LayoutLoad } from './$types';

// SPA-only: render entirely on the client. No SSR, no server load.
export const ssr = false;

// Single current-session user; cached so the app can still boot offline.
const USER_CACHE_KEY = 'me:user';

export const load: LayoutLoad = async ({ fetch, depends }) => {
	depends('app:current-user');

	const client = createApiClient();

	// `null` is a real cached value here (logged out), distinct from a cache miss,
	// so the type is `CurrentUserDTO | null`. The fetcher never returns `undefined`.
	const { data } = await fetchWithCache<CurrentUserDTO | null>({
		key: USER_CACHE_KEY,
		fetcher: async ({ signal }) => {
			const { data, response, error } = await client.GET('/me/', { fetch, signal });
			// Guest, or stale/invalid session → cache and return "logged out".
			if (response.status === 401 || response.status === 403 || error || !data) {
				return null;
			}
			return data;
		}
	});

	// A complete cache miss (offline first boot) is also "not logged in".
	return { user: data ?? null };
};
