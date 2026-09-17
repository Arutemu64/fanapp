import type { PersistedClient, Persister } from '@tanstack/query-persist-client-core';
import type { Query } from '@tanstack/svelte-query';

import {
	persistQueryClientRestore,
	persistQueryClientSubscribe
} from '@tanstack/query-persist-client-core';
import { QueryClient } from '@tanstack/svelte-query';
import { createStore, del, get, set, type UseStore } from 'idb-keyval';

/**
 * The single TanStack Query cache: every network read in the app goes through it,
 * so invalidation, background refetches and offline reads share one source of
 * truth.
 *
 * Offline support is the persister below — the dehydrated cache is written to
 * IndexedDB and restored before the first load runs, so a cold boot with no
 * network paints the last synced copy instead of an error.
 */

// How long a persisted entry stays usable. Deliberately long: the festival runs
// over a weekend on venue wifi that is routinely unusable, and a stale programme
// beats an empty screen. `gcTime` must be at least this, or a query is collected
// out of the in-memory cache before it can ever be dehydrated.
//
// Capped at 21 days rather than a round month because `gcTime` becomes a
// `setTimeout` delay, which overflows a signed 32-bit int past ~24.8 days and
// then fires almost immediately — silently collecting the very entries this is
// meant to keep. Supporting a longer delay needs a custom `TimeoutProvider`
// (https://tanstack.com/query/latest/docs/reference/TimeoutManager), which is
// not worth it for a weekend convention.
const OFFLINE_CACHE_MAX_AGE_MS = 21 * 24 * 60 * 60 * 1000;

// Bump to discard every persisted cache on deploy (e.g. after a breaking change
// to a response shape that hydrated data would no longer satisfy).
const PERSIST_BUSTER = 'v1';

/**
 * Options to spread into a query that must survive a reload and be readable
 * offline. `networkMode: 'offlineFirst'` makes TanStack run the fetch even when
 * the browser reports offline — `navigator.onLine` lies on captive wifi and a
 * dead VPN — and fall back to the cached data when it fails, rather than parking
 * the query in `paused` and painting nothing.
 */
export const offlineQueryOptions = {
	gcTime: OFFLINE_CACHE_MAX_AGE_MS,
	networkMode: 'offlineFirst'
} as const;

/**
 * Options to spread into a query that must never be served from a stale copy.
 *
 * Voting is the case this exists for: casting a vote is a mutation, and the
 * open/closed and already-voted state must be live — a cached ballot you cannot
 * submit is a dead end. `networkMode: 'online'` parks the query as `paused` while
 * offline, which is how the page knows to show an honest "online only" state
 * rather than an empty list, and `gcTime: 0` drops the answer as soon as nothing
 * is reading it.
 */
export const onlineOnlyQueryOptions = {
	gcTime: 0,
	staleTime: 0,
	networkMode: 'online'
} as const;

// Operations whose responses carry no identity: one cached copy serves guests and
// every account, and it survives logout. Everything else is treated as the
// viewer's own data and is dropped on logout, so it can never surface for the
// next account on a shared device — an unknown operation defaults to user-scoped
// on purpose, so adding an endpoint cannot leak it by omission.
const UNIVERSAL_OPERATIONS: ReadonlySet<string> = new Set([
	'debug',
	'getPublicConfig',
	'getSchedule',
	'healthCheck',
	'listOauthProviders'
]);

// Operations worth keeping on disk for an offline boot. Everything else stays
// memory-only: staff tools and voting are live surfaces where a stale copy
// misrepresents the world (a cached ballot you cannot submit is a dead end), so
// they must not be served from a cold cache.
const PERSISTED_OPERATIONS: ReadonlySet<string> = new Set([
	'getCurrentUser',
	'getPublicConfig',
	'getSchedule',
	'getSubscriptions',
	'listUserNotifications',
	'countUnreadNotifications'
]);

/**
 * The operation a generated query key belongs to.
 *
 * Hey-API keys are a single-element tuple whose object carries `_id` (the
 * operation name) alongside the request's path/query, so every variant of one
 * endpoint shares an `_id`.
 */
function operationOf(queryKey: readonly unknown[]): string | undefined {
	const head = queryKey[0];
	if (typeof head !== 'object' || head === null) return undefined;
	const id = (head as { _id?: unknown })._id;
	return typeof id === 'string' ? id : undefined;
}

/** True when a query holds data belonging to the signed-in user. */
function isUserScoped(query: Query): boolean {
	const operation = operationOf(query.queryKey);
	return operation === undefined || !UNIVERSAL_OPERATIONS.has(operation);
}

export function createQueryClient(): QueryClient {
	return new QueryClient({
		defaultOptions: {
			queries: {
				// Long enough that moving between pages reuses what the app already has,
				// short enough that returning to a tab after a while refetches. Freshness
				// within a session is driven by SSE-triggered invalidation, not polling.
				staleTime: 30 * 1000,
				gcTime: OFFLINE_CACHE_MAX_AGE_MS,
				networkMode: 'offlineFirst',
				// One retry only: on venue wifi the default three turn a failed first
				// paint into a long spinner, and the cached copy is the better answer.
				retry: 1,
				refetchOnWindowFocus: false
			},
			mutations: {
				// A mutation must never be replayed from a queued offline state — the
				// app has its own explicit offline queue for the writes that support it.
				networkMode: 'online'
			}
		}
	});
}

/**
 * IndexedDB persister.
 *
 * IndexedDB rather than localStorage because the dehydrated schedule is far past
 * the 5MB localStorage budget and a synchronous write of it would jank the main
 * thread. Every method swallows storage errors (private mode, disabled storage,
 * quota) and degrades to "nothing persisted" — offline caching is best-effort and
 * must never break a normal online load.
 *
 * @see https://tanstack.com/query/latest/docs/framework/react/plugins/persistQueryClient
 */
function createIdbPersister(): Persister {
	// One database, one store, one key. idb-keyval's default store would be shared
	// with any other use of the library; a named store keeps the cache self-contained.
	const store: UseStore = createStore('fanfan-query-cache', 'keyval');
	const cacheKey = 'query-cache';

	return {
		persistClient: async (client: PersistedClient) => {
			try {
				await set(cacheKey, client, store);
			} catch {
				// Ignore — storage may be unavailable or full.
			}
		},
		restoreClient: async () => {
			try {
				return await get<PersistedClient>(cacheKey, store);
			} catch {
				return undefined;
			}
		},
		removeClient: async () => {
			try {
				await del(cacheKey, store);
			} catch {
				// Ignore — see above.
			}
		}
	};
}

/**
 * Hydrate the persisted cache, then keep writing it back as the cache changes.
 * Returns an unsubscribe function.
 *
 * The restore is awaited *before* any route load runs (the root layout load does
 * this), which is what makes an offline cold boot paint real data: a query that
 * mounted while the restore was still in flight would race it and refetch into an
 * empty cache instead.
 */
export async function restoreQueryCache(queryClient: QueryClient): Promise<() => void> {
	const persister = createIdbPersister();

	await persistQueryClientRestore({
		queryClient,
		persister,
		maxAge: OFFLINE_CACHE_MAX_AGE_MS,
		buster: PERSIST_BUSTER
	});

	return persistQueryClientSubscribe({
		queryClient,
		persister,
		buster: PERSIST_BUSTER,
		dehydrateOptions: {
			// Only successful reads from the offline whitelist reach disk: an errored
			// or still-pending query would hydrate as a broken entry on the next boot.
			shouldDehydrateQuery: (query: Query) => {
				const operation = operationOf(query.queryKey);
				return (
					query.state.status === 'success' &&
					operation !== undefined &&
					PERSISTED_OPERATIONS.has(operation)
				);
			}
		}
	});
}

/**
 * Drop every query holding the signed-in user's data, on logout or session loss,
 * so the next account never reads the previous user's schedule subscriptions or
 * notifications on a shared device. Universal entries (public config, the
 * programme) are left in place so they still serve the next viewer offline.
 *
 * `removeQueries` rather than `invalidateQueries`: an invalidated query keeps its
 * data and would still render while the refetch is in flight.
 */
export function clearUserQueries(queryClient: QueryClient): void {
	queryClient.removeQueries({ predicate: isUserScoped });
}
