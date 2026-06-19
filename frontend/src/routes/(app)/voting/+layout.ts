import { createApiClient } from '$lib/api';
import { fetchWithCache } from '$lib/utils/offlineCache';
import type { GetVotingStateResult } from '$lib/types/voting';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ fetch, parent }) => {
	const { user } = await parent();
	// Per-user key: status/can_vote depend on the viewer's auth and ticket.
	const cacheKey = `voting:status:${user?.id ?? 'guest'}`;

	const client = createApiClient();

	// Cache the status so can_vote/the alert still render correctly offline. The
	// vote itself is a POST validated server-side, so a stale "open" never lets a
	// bad vote through — it just fails and refreshes on reconnect.
	const { data } = await fetchWithCache<GetVotingStateResult>({
		key: cacheKey,
		fetcher: async ({ signal }) => {
			const { data, error } = await client.GET('/voting/status', { fetch, signal });
			// Reachable but errored → fall back to cache.
			if (error || !data) return undefined;
			return data;
		}
	});

	// Undefined (offline first boot, nothing cached) keeps the prior soft behavior:
	// the alert simply hides and pages treat can_vote as false.
	return { votingStatus: data };
};
