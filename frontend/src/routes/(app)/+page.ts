import type { PublicConfigDto } from '$lib/api/generated';

import { createApiClient } from '$lib/api';
import { getPublicConfig } from '$lib/api/generated';
import { CONFIG_CACHE_KEY, FALLBACK_CONFIG } from '$lib/constants/festival';
import { fetchWithCache, universalScope } from '$lib/utils/offlineCache';
import { loadScheduleWithSubscriptions } from '$lib/utils/scheduleData';
import { fetchVotingStatus } from '$lib/utils/votingStatus';

import type { PageLoad } from './$types';

// Public config drives the hero's phase (before/during/after) and countdown, so it
// must render for guests and offline. Network-first with a fallback to the last
// synced copy (fetchWithCache, universal store — no per-user data), matching the
// schedule. Network-first over stale-while-revalidate on purpose: the phase is a
// decision, so a client opening the app after the festival ends must not first
// paint a stale countdown. A complete cache miss (first-ever visit made offline)
// falls back to the shipped defaults; any live response wins over both.
async function loadConfig(fetch: typeof globalThis.fetch): Promise<PublicConfigDto> {
	const client = createApiClient();

	const { data } = await fetchWithCache<PublicConfigDto>({
		key: CONFIG_CACHE_KEY,
		scope: universalScope,
		fetcher: async ({ signal }) => {
			const { data, error } = await getPublicConfig({ client, fetch, signal });
			return error ? undefined : data;
		}
	});

	return data ?? FALLBACK_CONFIG;
}

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	// 'app:config' also covers the voting window, which organizers edit in settings.
	depends('app:config');
	depends('app:schedule');

	// Reading the user through parent() re-runs this load on login, logout and a
	// linked ticket, which is what changes the voting status and subscriptions.
	const { user } = await parent();

	const [config, scheduleResult, votingStatus] = await Promise.all([
		loadConfig(fetch),
		loadScheduleWithSubscriptions(fetch, user?.id),
		// Optional here: a failure hides the voting card and nothing else.
		fetchVotingStatus(fetch, { reportUnreachable: false })
	]);

	// A schedule miss is not an error here: home just leaves out what needs it.
	return {
		// AppNavbar renders this as the page <h1>; it matches the tab label, as on
		// every other tab.
		title: 'Главная',
		config,
		schedule: scheduleResult.schedule ?? [],
		scheduleStale: scheduleResult.stale,
		scheduleCachedAt: scheduleResult.cachedAt,
		votingStatus
	};
};
