import { clear, get, set } from 'idb-keyval';

/**
 * Thin wrappers over IndexedDB (via idb-keyval) for persisting the last good
 * copy of read-only API data, so pages can serve it when the network is down.
 *
 * Both helpers swallow storage errors (private mode, disabled storage, quota)
 * and degrade to a cache miss / no-op — offline caching is best-effort and must
 * never break a normal online load.
 */

export async function readCache<T>(key: string): Promise<T | undefined> {
	try {
		return await get<T>(key);
	} catch {
		return undefined;
	}
}

export async function writeCache<T>(key: string, value: T): Promise<void> {
	try {
		await set(key, value);
	} catch {
		// Ignore — storage may be unavailable or full.
	}
}

/**
 * Drop every cached entry. Called on logout so the next account never reads the
 * previous user's cached data (e.g. their schedule subscriptions) on a shared
 * device. Swallows storage errors like the other helpers.
 */
export async function clearCache(): Promise<void> {
	try {
		await clear();
	} catch {
		// Ignore — storage may be unavailable.
	}
}
