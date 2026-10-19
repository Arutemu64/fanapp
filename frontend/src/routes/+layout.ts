import { version } from '$app/env';
import * as Sentry from '@sentry/sveltekit';
import { MutationCache, QueryCache, QueryClient } from '@tanstack/svelte-query';
import { persistQueryClient } from '@tanstack/svelte-query-persist-client';

import { gotNoApiAnswer, isUnexpectedRequestError } from '#lib/api/errors.js';
import { CACHE_MAX_AGE_MS, isOfflineQuery, OFFLINE_QUERY_KEYS } from '#lib/api/offlineQueries.js';
import { createIdbPersister } from '#lib/api/queryPersister.js';
import { registerQueuedWrites, shouldPersistMutation } from '#lib/api/writeQueue.js';
import { settleIdentityForBoot } from '#lib/services/identity.js';

import type { LayoutLoad } from './$types';

// SPA-only: render entirely on the client. There is no server render.
export const ssr = false;

// API error bodies and dropped connections are expected and reported elsewhere
// (the backend files its own errors), so only a failure in our own query code is
// sent. Without a DSN, Sentry was never initialised and this is a no-op.
function reportUnexpectedRequestError(error: unknown) {
	if (isUnexpectedRequestError(error)) {
		Sentry.captureException(error, { tags: { source: 'tanstack-query' } });
	}
}

// Runs once per page load: nothing here reads `url` or calls `depends`, and the
// app never calls `invalidateAll`/`refreshAll`, so the QueryClient — and the
// cache in it — lives for the whole session. Without SSR a module singleton
// would be just as safe from cross-user leaks; it is load data so `Session`
// receives the same cache the app reads and resets it on each identity
// transition: login marks every query stale, logout and expiry drop the
// inactive ones and mark the rest stale to refetch as the guest.
export const load: LayoutLoad = async () => {
	const queryClient = new QueryClient({
		// A failed query or mutation is caught by TanStack Query, so it never reaches
		// `handleError` (hooks.client.ts). The cache-level callbacks run once per
		// failure, not once per subscribed component, which makes them the place for
		// error tracking (https://tkdodo.eu/blog/react-query-error-handling).
		queryCache: new QueryCache({ onError: reportUnexpectedRequestError }),
		mutationCache: new MutationCache({ onError: reportUnexpectedRequestError }),
		defaultOptions: {
			queries: {
				// Data a load prefetched on hover/tap stays fresh when the page mounts a
				// moment later, rather than being refetched straight away
				// (https://tanstack.com/query/latest/docs/framework/react/guides/prefetching).
				// Live data doesn't wait it out: SSE events and mutations invalidate, which
				// refetches regardless of staleTime.
				staleTime: 60 * 1000,
				// Retry only a request that got no API answer — a network failure, a
				// timeout, a gateway page. An API error (401, 404, validation) is the
				// server's verdict, and a bug in our own query code fails the same way
				// every time; repeating either only delays showing it by seconds.
				retry: (failureCount, error) => failureCount < 3 && gotNoApiAnswer(error)
			},
			mutations: {
				// Every write is online-only (ADR-0022): it must fail at once with the
				// connection message, not wait out an offline spell in TanStack's default
				// `online` mode and then fire unseen once reachability — which drives
				// onlineManager — comes back.
				// https://tanstack.com/query/latest/docs/framework/react/guides/network-mode
				networkMode: 'always'
			}
		}
	});
	// Set before the restore below: restored queries and queued writes take their
	// options from here.
	for (const queryKey of OFFLINE_QUERY_KEYS) {
		queryClient.setQueryDefaults(queryKey, { gcTime: CACHE_MAX_AGE_MS });
	}
	registerQueuedWrites(queryClient);

	// One IndexedDB entry holds the offline queries, so those screens open offline
	// once they have loaded. Restored before any guard reads identity from it.
	// The build `version` busts it on deploy, so a client never reads a payload
	// shaped by an older API.
	// TODO: bust only the queries whose response shape a deploy changed — a deploy
	// applied just before a mobile shutdown wipes the saved programme and the
	// queued writes; deferred as more machinery than it is worth for now.
	const [, restored] = persistQueryClient({
		queryClient,
		persister: createIdbPersister(),
		maxAge: CACHE_MAX_AGE_MS,
		buster: version,
		dehydrateOptions: {
			// Not TanStack's default (successful queries only): a refetch that failed
			// leaves the query in error with its last good data, and dropping it here
			// would erase the saved programme right when the network is bad.
			shouldDehydrateQuery: (query) =>
				isOfflineQuery(query.queryKey) && query.state.data !== undefined,
			shouldDehydrateMutation: shouldPersistMutation
		}
	});
	await restored;

	// Identity gates the route guards, so settle it before any child load reads it.
	await settleIdentityForBoot(queryClient);

	return { queryClient };
};
