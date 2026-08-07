import { createApiClient } from '$lib/api';
import { CONFIG_CACHE_KEY, FALLBACK_CONFIG, type PublicConfig } from '$lib/constants/festival';
import { fetchWithCache, universalScope } from '$lib/utils/offlineCache';

import type { PageLoad } from './$types';

// Public config drives the hero's phase (before/during/after) and countdown, so it
// must render for guests and offline. Network-first with a fallback to the last
// synced copy (fetchWithCache, universal store — no per-user data), matching the
// schedule. Network-first over stale-while-revalidate on purpose: the phase is a
// decision, so a client opening the app after the festival ends must not first
// paint a stale countdown. A complete cache miss (first-ever visit made offline)
// falls back to the shipped defaults; any live response wins over both.
export const load: PageLoad = async ({ fetch, depends }) => {
	depends('app:config');

	const client = createApiClient();

	const { data } = await fetchWithCache<PublicConfig>({
		key: CONFIG_CACHE_KEY,
		scope: universalScope,
		fetcher: async ({ signal }) => {
			const { data, error } = await client.GET('/config', { fetch, signal });
			return error ? undefined : data;
		}
	});

	return { config: data ?? FALLBACK_CONFIG };
};
