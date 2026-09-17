import type { PersistedClient, Persister } from '@tanstack/query-persist-client-core';

import { persistQueryClient } from '@tanstack/query-persist-client-core';
import { QueryClient } from '@tanstack/svelte-query';
import { del, get, set } from 'idb-keyval';

/**
 * The single TanStack Query cache for the whole SPA. Every read, its cached copy
 * and its invalidation flow through this client — there is no second data path
 * (no bespoke IndexedDB cache, no manual storage sync). Live SSE events and the
 * offline→online recovery both converge here by invalidating query keys, so the
 * UI state, background refetches and offline persistence stay unified.
 */

// One IndexedDB key holds the entire dehydrated cache. idb-keyval opens a single
// database/store, so there is no cross-database first-upgrade race (the reason the
// old cache also kept everything in one store — see the note that used to live in
// offlineCache.ts / idb-keyval issue #32).
const PERSIST_KEY = 'fanfan-query-cache';

// Bumped when the cache shape changes incompatibly; a mismatch discards the
// persisted blob on restore instead of hydrating stale-shaped entries.
const PERSIST_BUSTER = 'v1';

// gcTime must outlive the gap between sessions, or the persister garbage-collects
// entries before the next boot can rehydrate them and offline first paint is empty.
const PERSIST_GC_TIME = 1000 * 60 * 60 * 24; // 24h

// Drop persisted entries older than this on restore, so a cold offline boot never
// paints data from a previous festival day. Matches gcTime: the cache is only as
// trustworthy offline as it is fresh.
const PERSIST_MAX_AGE = PERSIST_GC_TIME;

/** idb-keyval-backed persister: the dehydrated client is one value under one key. */
function createIdbPersister(): Persister {
	return {
		persistClient: (client: PersistedClient) => set(PERSIST_KEY, client),
		restoreClient: () => get<PersistedClient>(PERSIST_KEY),
		removeClient: () => del(PERSIST_KEY)
	};
}

// App-lifetime reference to the active client, so plain modules that run outside
// a component or a `load` (the response interceptor, the reconnect catch-up) can
// invalidate query keys. Not user/session state — the cache it points at is wiped
// on logout by clearPersistedCache — so a module-held reference is safe here, the
// same way reachability state is module-global.
let active: QueryClient | null = null;

export function setActiveQueryClient(client: QueryClient): void {
	active = client;
}

export function getActiveQueryClient(): QueryClient | null {
	return active;
}

export function createQueryClient(): QueryClient {
	return new QueryClient({
		defaultOptions: {
			queries: {
				// Serve cached data while offline and fall back to the network only when
				// there is none, so offline route access works without a bespoke cache.
				networkMode: 'offlineFirst',
				// Long enough to survive a boot; the SSE stream and the reconnect
				// catch-up drive freshness by invalidating keys, so a big staleTime here
				// does not mean stale UI — it means we don't refetch on every mount.
				staleTime: 1000 * 30,
				gcTime: PERSIST_GC_TIME,
				// A cold offline mount should surface its empty state immediately rather
				// than retrying a doomed request; reconnect invalidation refetches later.
				retry: 1
			},
			mutations: {
				networkMode: 'offlineFirst'
			}
		}
	});
}

/**
 * Restore the persisted cache into `queryClient` and keep it synced to IndexedDB.
 * Returns once the initial restore settles, so callers can render from a warm
 * cache on first paint. Browser-only — never called during SSR (which this app
 * does not do anyway). Returns the unsubscribe from the ongoing persistence.
 */
export async function startPersistence(queryClient: QueryClient): Promise<() => void> {
	const [unsubscribe, restored] = persistQueryClient({
		queryClient,
		persister: createIdbPersister(),
		maxAge: PERSIST_MAX_AGE,
		buster: PERSIST_BUSTER
	});
	await restored;
	return unsubscribe;
}

/**
 * Wipe the entire cache — memory and persisted blob — on logout / session loss.
 *
 * Everything goes, not just per-user keys: a shared IndexedDB blob makes
 * enumerating "user-scoped" entries the same bespoke scoping the migration
 * removed, and wiping all of it is the leak-proof default (no per-user entry can
 * survive for the next account on a shared device). The cost is a cold cache for
 * universal data like the schedule after logout; it refetches on the next online
 * load. Awaiting the persister removal guarantees the blob is gone before a new
 * session can hydrate from it.
 */
export async function clearPersistedCache(queryClient: QueryClient): Promise<void> {
	queryClient.clear();
	try {
		await del(PERSIST_KEY);
	} catch {
		// Best-effort: storage may be unavailable (private mode, quota). A failed
		// removal only means a stale blob lingers until the next successful write.
	}
}
