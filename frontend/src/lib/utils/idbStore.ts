import { createStore, type UseStore } from 'idb-keyval';

/**
 * The app's single IndexedDB database, shared by every persistent client-side
 * cache (the TanStack Query persister in `$lib/query/persister.ts` and the
 * identity entry in `$lib/utils/offlineCache.ts`).
 *
 * Why one database for all of them: opening two idb-keyval databases concurrently
 * (each triggering its own first-time upgrade) races in Firefox — it loses the
 * upgrade on the second database, leaving it permanently unusable so every write
 * throws and is silently swallowed. A single database has a single open/upgrade,
 * so there is no race. See idb-keyval issue #32.
 *
 * Callers must swallow storage errors (private mode, disabled storage, quota) and
 * degrade to a cache miss / no-op — offline caching is best-effort and must never
 * break a normal online load.
 */
export const cacheStore: UseStore = createStore('fanfan-cache', 'keyval');
