import type { PersistedClient, Persister } from '@tanstack/query-persist-client-core';
import type { PersistQueryClientOptions } from '@tanstack/svelte-query-persist-client';

import { cacheStore } from '$lib/utils/idbStore';
import { removeOldestQuery } from '@tanstack/query-persist-client-core';
import { del, get, set } from 'idb-keyval';

import { persistScopeOf } from './persist';

// One entry holds the whole dehydrated cache. IndexedDB (not localStorage): the
// snapshot carries the full schedule, writes are async so they never block the
// main thread, and there is no ~5MB string quota to trip over.
const PERSISTED_CLIENT_KEY = 'q:client';

/**
 * Bump to discard every persisted cache after a change that makes old snapshots
 * unusable — a reshaped query key, or a DTO whose old form would render wrong.
 * Deliberately NOT the build hash: busting on every deploy would empty the
 * offline cache of anyone who updates the PWA while away from the network.
 */
const PERSISTED_CLIENT_BUSTER = 'v1';

/** Discard a snapshot older than this instead of restoring it. */
const PERSISTED_CLIENT_MAX_AGE_MS = 1000 * 60 * 60 * 24 * 7;

/**
 * Persist the query cache into the app's IndexedDB database.
 *
 * Every method swallows storage errors and degrades to a miss / no-op: private
 * mode, disabled storage and quota failures must cost the visitor their offline
 * copy, never a working online app.
 */
function createIdbPersister(): Persister {
	return {
		persistClient: async (client: PersistedClient) => {
			// A quota failure is retried against a smaller snapshot — `removeOldestQuery`
			// drops the least recently updated query each round — so a cache that has
			// outgrown the device's budget degrades to its freshest entries instead of
			// losing offline support entirely. Any other failure (private mode, storage
			// disabled) exhausts the snapshot and leaves the app online-only.
			let snapshot: PersistedClient | undefined = client;
			let errorCount = 0;

			while (snapshot) {
				try {
					await set(PERSISTED_CLIENT_KEY, snapshot, cacheStore);
					return;
				} catch (error) {
					errorCount += 1;
					snapshot = removeOldestQuery({
						persistedClient: snapshot,
						error: error instanceof Error ? error : new Error(String(error)),
						errorCount
					});
				}
			}
		},
		restoreClient: async () => {
			try {
				return await get<PersistedClient>(PERSISTED_CLIENT_KEY, cacheStore);
			} catch {
				return undefined;
			}
		},
		removeClient: async () => {
			try {
				await del(PERSISTED_CLIENT_KEY, cacheStore);
			} catch {
				// Ignore — same reason as above.
			}
		}
	};
}

/**
 * Options for `<PersistQueryClientProvider>` in the root layout.
 *
 * Only queries tagged by {@link persisted} and currently holding data are
 * written, so persistence stays an explicit per-query decision (see
 * `persist.ts`) rather than a side effect of having fetched something once.
 */
export function createPersistOptions(): Omit<PersistQueryClientOptions, 'queryClient'> {
	return {
		persister: createIdbPersister(),
		buster: PERSISTED_CLIENT_BUSTER,
		maxAge: PERSISTED_CLIENT_MAX_AGE_MS,
		dehydrateOptions: {
			shouldDehydrateQuery: (query) =>
				persistScopeOf(query.meta) !== undefined && query.state.status === 'success',
			// Mutations are online-only across the app (votes, settings, subscriptions);
			// persisting them would resurrect a write the user has no way to cancel.
			shouldDehydrateMutation: () => false
		}
	};
}
