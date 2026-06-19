import { error } from '@sveltejs/kit';
import { createApiClient } from '$lib/api';
import { fetchWithCache } from '$lib/utils/offlineCache';
import type { NominationVotingDTO } from '$lib/types/nominations';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, parent }) => {
	const { user } = await parent();
	// Per-user key: NominationVotingDTO carries the viewer's own user_vote.
	const cacheKey = `voting:nominations:${user?.id ?? 'guest'}`;

	const client = createApiClient();

	const { data, stale } = await fetchWithCache<NominationVotingDTO[]>({
		key: cacheKey,
		fetcher: async ({ signal }) => {
			const { data, error: fetchError } = await client.GET('/voting/nominations', {
				fetch,
				signal
			});
			// Reachable but errored → fall back to cache.
			if (fetchError || !data) return undefined;
			return data.nominations ?? [];
		}
	});

	// Complete miss (errored/offline with nothing cached): hard failure.
	if (data === undefined) {
		error(503, 'Не удалось загрузить номинации');
	}

	return {
		title: 'Голосование',
		nominations: data,
		stale
	};
};
