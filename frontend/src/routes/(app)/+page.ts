import { createApiClient } from '$lib/api';
import { FALLBACK_FESTIVAL_START } from '$lib/constants/festival';

import type { PageLoad } from './$types';

// Public config drives the hero's phase (before/during/after) and countdown.
// It must render for guests and on a cold or offline load, so the request is
// best-effort: any failure falls back to the shipped default start rather than
// blocking the page. The server value wins whenever /config is reachable.
export const load: PageLoad = async ({ fetch, depends }) => {
	depends('app:config');

	const fallback = {
		festival_start: FALLBACK_FESTIVAL_START,
		festival_ended: false,
		voting_enabled: false
	};

	const client = createApiClient();

	try {
		const { data, error } = await client.GET('/config', { fetch });
		return { config: error || !data ? fallback : data };
	} catch {
		return { config: fallback };
	}
};
