import { error } from '@sveltejs/kit';
import { createApiClient } from '$lib/api';
import { fetchWithCache } from '$lib/utils/offlineCache';
import type { GetVotingNominationResult } from '$lib/types/voting';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch, depends, parent }) => {
	depends('app:voting:nomination');

	const { user } = await parent();
	// Per-user key (per nomination): participants carry the viewer's own user_vote.
	const cacheKey = `voting:nomination:${params.nominationCode}:${user?.id ?? 'guest'}`;

	const client = createApiClient();

	const { data, stale } = await fetchWithCache<GetVotingNominationResult>({
		key: cacheKey,
		fetcher: async ({ signal }) => {
			const { data, error: apiError } = await client.GET('/voting/nominations/{nomination_code}', {
				fetch,
				signal,
				params: {
					path: {
						nomination_code: params.nominationCode
					}
				}
			});
			// Reachable but errored → fall back to cache.
			if (apiError || !data) return undefined;
			return data;
		}
	});

	// Complete miss (errored/offline with nothing cached): treat as not found.
	if (data === undefined) {
		error(404, 'Номинация не найдена');
	}

	return {
		title: 'Голосование',
		nomination: data,
		stale
	};
};
