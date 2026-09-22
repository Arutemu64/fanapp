import type { PersistedClient, Persister } from '@tanstack/query-persist-client-core';

import { createStore, del, get, set, type UseStore } from 'idb-keyval';

/**
 * IndexedDB persister for the query cache, so every route renders from its last
 * synced data on an offline boot.
 *
 * One idb-keyval database, opened once: opening two concurrently (each running
 * its own first-time upgrade) races in Firefox, which loses the upgrade on the
 * second database and leaves it permanently unusable. Any future IndexedDB use
 * must share this store rather than call idb-keyval's default `get`/`set`, which
 * would open a second database. See idb-keyval issue #32.
 */
const cacheStore: UseStore = createStore('fanfan-query-cache', 'keyval');

const CLIENT_KEY = 'query-client';

// The hand-rolled offline cache this replaced. Its entries are per-user and
// nothing reads or clears them any more, so an upgraded device would keep the
// previous account's data in IndexedDB forever. Dropped once, best-effort, on the
// first boot after the upgrade; deleting a database that is already gone resolves
// without error, so this costs one no-op request per boot thereafter.
const LEGACY_CACHE_DB = 'fanfan-cache';

function dropLegacyCache(): void {
	try {
		indexedDB.deleteDatabase(LEGACY_CACHE_DB);
	} catch {
		// Storage may be unavailable (private mode, blocked site data) — best-effort.
	}
}

/**
 * Holds no session state of its own — just the store handle — so unlike the
 * QueryClient it is safe to share as a module constant.
 */
export const idbPersister: Persister = {
	persistClient: async (client: PersistedClient) => {
		await set(CLIENT_KEY, client, cacheStore);
	},
	removeClient: async () => {
		await del(CLIENT_KEY, cacheStore);
	},
	restoreClient: async () => {
		dropLegacyCache();
		return await get<PersistedClient>(CLIENT_KEY, cacheStore);
	}
};
