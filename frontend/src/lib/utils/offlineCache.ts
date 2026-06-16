import { clear, get, set } from 'idb-keyval';
import { isReachable, markReachable } from '$lib/services/reachability';
import { timeoutSignal, FIRST_PAINT_TIMEOUT_MS } from '$lib/utils/fetchTimeout';

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

/** Result of a {@link fetchWithCache} call. */
export interface FetchWithCacheResult<T> {
	/** Fresh value, last cached copy, or `undefined` on a complete miss. */
	data: T | undefined;
	/** `true` when served from cache (the live fetch was skipped or failed). */
	stale: boolean;
}

/** Options for {@link fetchWithCache}. */
export interface FetchWithCacheOptions<T> {
	/** IndexedDB key; should be per-user when the data is user-specific. */
	key: string;
	/**
	 * Runs the network request, given a timeout `signal` to pass to the API call.
	 * Return the value to cache, or `undefined` to signal "reachable but no usable
	 * data" (e.g. an HTTP error) — that falls back to the cache like an outage.
	 * Throwing is treated as a network failure (offline / timeout).
	 */
	fetcher: (ctx: { signal: AbortSignal }) => Promise<T | undefined>;
	/** First-paint timeout budget; defaults to {@link FIRST_PAINT_TIMEOUT_MS}. */
	timeoutMs?: number;
}

/**
 * The shared offline-fetch flow used by read-only `load` functions:
 *
 *   1. If the server is known unreachable, skip the doomed request and serve the
 *      cached copy immediately so first paint isn't blocked.
 *   2. Otherwise run `fetcher` under a timeout. A resolved promise proves the
 *      server answered (`markReachable(true)`); a returned value is cached and
 *      returned fresh, while `undefined` falls back to the cache.
 *   3. A thrown error (network failure / timeout) marks us unreachable and serves
 *      the cached copy.
 *
 * `fetcher` should close over the `load`'s own `fetch` so SvelteKit can track the
 * request; this helper only supplies the timeout `signal`.
 */
export async function fetchWithCache<T>({
	key,
	fetcher,
	timeoutMs = FIRST_PAINT_TIMEOUT_MS
}: FetchWithCacheOptions<T>): Promise<FetchWithCacheResult<T>> {
	// Known unreachable: serve the cached copy without a dead network wait.
	if (!isReachable()) {
		return { data: await readCache<T>(key), stale: true };
	}

	try {
		const value = await fetcher({ signal: timeoutSignal(timeoutMs) });
		// Resolved → the server responded, even if the payload was unusable.
		markReachable(true);

		if (value === undefined) {
			// Reachable but errored/empty — prefer the cached copy over a hard failure.
			return { data: await readCache<T>(key), stale: true };
		}

		void writeCache<T>(key, value);
		return { data: value, stale: false };
	} catch {
		// Network failure / timeout: serve the last synced copy.
		markReachable(false);
		return { data: await readCache<T>(key), stale: true };
	}
}
