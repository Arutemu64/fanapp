import { version } from '$app/env';
import * as Sentry from '@sentry/sveltekit';
import { MutationCache, QueryCache, QueryClient } from '@tanstack/svelte-query';
import { persistQueryClient } from '@tanstack/svelte-query-persist-client';

import { gotNoApiAnswer, isUnexpectedRequestError } from '#lib/api/errors.js';
import {
	countUnreadNotificationsQueryKey,
	getCurrentUserQueryKey,
	getPublicConfigQueryKey,
	getScheduleQueryKey,
	getSubscriptionsQueryKey,
	listUserNotificationsQueryKey
} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { currentUserOptions, queryForLoad } from '#lib/api/index.js';
import { createIdbPersister } from '#lib/api/queryPersister.js';
import { isLogoutPending } from '#lib/utils/pendingLogout.js';

import type { LayoutLoad } from './$types';

// SPA-only: render entirely on the client. There is no server render.
export const ssr = false;

// The screens that must open offline: the identity the guards and the profile
// read, the home hero, the programme with the viewer's subscriptions, and the
// notifications with their badge. Only these are written to IndexedDB. Every
// other query is online-only: fetched fresh after a cold start and dropped from
// memory five minutes after its screen closes (TanStack's default gcTime) —
// voting must not show a stale ballot, and the organizer tools hold other people's
// details that have no business on the device.
const OFFLINE_QUERY_KEYS = [
	getCurrentUserQueryKey(),
	getPublicConfigQueryKey(),
	getScheduleQueryKey(),
	getSubscriptionsQueryKey(),
	listUserNotificationsQueryKey(),
	countUnreadNotificationsQueryKey()
];
// Matched by operation id, the first part of every hey-api query key, so a
// list key also covers its paginated variant.
const OFFLINE_QUERY_IDS = new Set(OFFLINE_QUERY_KEYS.map(([{ _id }]) => _id));

// How long a cached copy may serve the app offline: a festival weekend plus the
// trip there and back, where the persister's 24h default would drop the
// programme for anyone who didn't open the app for a day. StaleDataNotice shows
// how old what's on screen is. The offline queries keep this gcTime too, or they
// are garbage-collected before they are ever persisted:
// https://tanstack.com/query/latest/docs/framework/react/plugins/persistQueryClient
const CACHE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;

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
	// Set before the restore below: restored queries take their options from here.
	for (const queryKey of OFFLINE_QUERY_KEYS) {
		queryClient.setQueryDefaults(queryKey, { gcTime: CACHE_MAX_AGE_MS });
	}

	// One IndexedDB entry holds the offline queries, so those screens open offline
	// once they have loaded. Restored before any guard reads identity from it.
	// The build `version` busts it on deploy, so a client never reads a payload
	// shaped by an older API.
	const [, restored] = persistQueryClient({
		queryClient,
		persister: createIdbPersister(),
		maxAge: CACHE_MAX_AGE_MS,
		buster: version,
		dehydrateOptions: {
			// Not TanStack's default (successful queries only): a refetch that failed
			// leaves the query in error with its last good data, and dropping it here
			// would erase the saved programme right when the network is bad.
			shouldDehydrateQuery: (query) => {
				const [{ _id }] = query.queryKey as [{ _id: string }];
				return OFFLINE_QUERY_IDS.has(_id) && query.state.data !== undefined;
			}
		}
	});
	await restored;

	// Identity gates the route guards, so settle it before any child load reads
	// it. A restored user answers at once (the components reading it revalidate,
	// and a /me 401 ends an expired session). A restored guest is re-checked: a
	// social login arrives here as a full page load with a fresh session cookie,
	// and trusting the saved `null` would bounce the new user to /login. A first
	// boot and a guest wait on /me no longer than first paint can afford. A pending
	// offline logout is re-checked too, whose queryFn answers `null` without the
	// network: the logout flag is saved at once but the cache only on the
	// persister's throttle, so a restart in between can restore the account the
	// user just left. A /me that fails leaves the user unknown, which only the
	// (protected) guard has to resolve: it asks the reachability probe itself, so
	// a guest opening Home or the programme on a dead network isn't held on the
	// splash for the probe's offline-confirm window as well.
	await queryForLoad(queryClient, {
		...currentUserOptions(),
		staleTime: (query) => (query.state.data && !isLogoutPending() ? 'static' : 0)
	}).catch(() => {});

	return { queryClient };
};
