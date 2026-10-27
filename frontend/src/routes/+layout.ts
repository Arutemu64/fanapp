import * as Sentry from '@sentry/sveltekit';
import { MutationCache, QueryCache, QueryClient } from '@tanstack/svelte-query';
import { persistQueryClient } from '@tanstack/svelte-query-persist-client';

import { gotNoApiAnswer, isUnexpectedRequestError } from '#lib/api/errors.js';
import {
	CACHE_MAX_AGE_MS,
	isOfflineQuery,
	OFFLINE_QUERY_KEYS,
	QUERY_CACHE_BUSTER
} from '#lib/api/offlineQueries.js';
import { createIdbPersister } from '#lib/api/queryPersister.js';
import { registerQueuedWrites, shouldPersistMutation } from '#lib/api/writeQueue.js';
import { settleIdentityForBoot } from '#lib/services/identity.js';

import type { LayoutLoad } from './$types';

export const ssr = false;

function reportUnexpectedRequestError(error: unknown) {
	if (isUnexpectedRequestError(error)) {
		Sentry.captureException(error, { tags: { source: 'tanstack-query' } });
	}
}

export const load: LayoutLoad = async () => {
	const queryClient = new QueryClient({
		queryCache: new QueryCache({ onError: reportUnexpectedRequestError }),
		mutationCache: new MutationCache({ onError: reportUnexpectedRequestError }),
		defaultOptions: {
			queries: {
				staleTime: 60 * 1000,
				retry: (failureCount, error) => failureCount < 3 && gotNoApiAnswer(error)
			},
			mutations: {
				networkMode: 'always'
			}
		}
	});
	for (const queryKey of OFFLINE_QUERY_KEYS) {
		queryClient.setQueryDefaults(queryKey, { gcTime: CACHE_MAX_AGE_MS });
	}
	registerQueuedWrites(queryClient);

	const [, restored] = persistQueryClient({
		queryClient,
		persister: createIdbPersister(),
		maxAge: CACHE_MAX_AGE_MS,
		buster: QUERY_CACHE_BUSTER,
		dehydrateOptions: {
			shouldDehydrateQuery: (query) =>
				isOfflineQuery(query.queryKey) && query.state.data !== undefined,
			shouldDehydrateMutation: shouldPersistMutation
		}
	});
	await restored;

	await settleIdentityForBoot(queryClient);

	return { queryClient };
};
