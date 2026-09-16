import { QueryClient } from '@tanstack/svelte-query';

import { persistScopeOf } from './persist';

/**
 * How long an unused query stays in memory. Must be at least the persister's
 * `maxAge`: a query garbage-collected from the cache is gone from the next
 * dehydrated snapshot too, so a shorter budget would quietly shrink what the app
 * can show offline.
 */
const QUERY_GC_TIME_MS = 1000 * 60 * 60 * 24 * 7;

/**
 * How long fetched data is served without a background refetch. Matches the
 * window the schedule page used to enforce by hand before refetching on
 * foreground, so a quick tab-flip still costs no request.
 */
const QUERY_STALE_TIME_MS = 30000;

/**
 * The app's QueryClient.
 *
 * Created by the root layout component (never a module singleton): the client
 * holds per-user data, and a module-level instance would outlive login/logout in
 * this SPA. `clearUserQueries` is what drops that data on logout.
 *
 * Reconnect and foreground refetching are left on — with `onlineManager` bound to
 * our own reachability probe (`bindOnlineManager`), "reconnect" means the backend
 * answered again, not merely that an interface appeared.
 */
export function createQueryClient(): QueryClient {
	return new QueryClient({
		defaultOptions: {
			queries: {
				gcTime: QUERY_GC_TIME_MS,
				staleTime: QUERY_STALE_TIME_MS,
				// The API's own 4xx are final — only the flaky cases are worth a second
				// attempt, and `networkMode: 'online'` already pauses (rather than
				// retries) while the backend is unreachable.
				retry: 1
			}
		}
	});
}

/**
 * Drop every query holding the signed-in user's data, so the next account on a
 * shared device cannot read it. Universal queries (schedule, festival config) are
 * left alone — they carry no identity and keep guests served offline.
 *
 * Removing from the cache is what clears storage too: the persister re-writes the
 * dehydrated snapshot on the next cache change, and removed queries are simply
 * not in it. Call on logout and on an authoritative 401/403, alongside
 * `clearUserCache()` for the identity entry.
 */
export function clearUserQueries(queryClient: QueryClient): void {
	queryClient.removeQueries({
		predicate: (query) => persistScopeOf(query.meta) === 'user'
	});
}
