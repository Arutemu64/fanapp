import { delMany, get, keys, set } from 'idb-keyval';
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

// Keys whose values belong to the signed-in user and MUST be dropped on logout /
// session loss so the next account never reads them on a shared device. Add every
// new per-user cache key here — this is the only list logout consults.
const USER_CACHE_EXACT_KEYS = ['me:user'];
const USER_CACHE_KEY_PREFIXES = ['subscriptions:', 'profile-connections:', 'notifications:'];

/**
 * Drop the signed-in user's cached entries on logout / session loss so the next
 * account never reads the previous user's data (e.g. their schedule subscriptions)
 * on a shared device. Universal caches like `schedule` carry no per-user data and
 * are intentionally left warm so they survive a logout and serve the next viewer.
 * Swallows storage errors like the other helpers.
 */
export async function clearUserCache(): Promise<void> {
	try {
		const allKeys = await keys();
		const toDelete = allKeys.filter(
			(k): k is string =>
				typeof k === 'string' &&
				(USER_CACHE_EXACT_KEYS.includes(k) ||
					USER_CACHE_KEY_PREFIXES.some((prefix) => k.startsWith(prefix)))
		);
		if (toDelete.length > 0) await delMany(toDelete);
	} catch {
		// Ignore — storage may be unavailable. Best-effort like the other helpers.
	}
}

/**
 * Stored shape for {@link fetchWithCache} entries: the cached value plus the
 * epoch-millis moment it was persisted, so pages can show "synced at …".
 */
interface CachedEnvelope<T> {
	value: T;
	cachedAt: number;
}

/** True when a read-back value is a {@link CachedEnvelope} (vs a legacy raw value). */
function isEnvelope<T>(raw: unknown): raw is CachedEnvelope<T> {
	return (
		typeof raw === 'object' &&
		raw !== null &&
		'value' in raw &&
		typeof (raw as { cachedAt?: unknown }).cachedAt === 'number'
	);
}

/**
 * Read an entry written by {@link fetchWithCache}, unwrapping the envelope.
 * Entries cached before the envelope migration are bare values — treat them as a
 * value with an unknown timestamp; the next online write upgrades them.
 */
async function readEnvelope<T>(key: string): Promise<{ value: T; cachedAt?: number } | undefined> {
	const raw = await readCache<unknown>(key);
	if (raw === undefined) return undefined;
	if (isEnvelope<T>(raw)) return { value: raw.value, cachedAt: raw.cachedAt };
	// Legacy raw value (incl. `null`, a valid "logged out" cache) — no timestamp.
	return { value: raw as T };
}

/** Result of a {@link fetchWithCache} call. */
export interface FetchWithCacheResult<T> {
	/** Fresh value, last cached copy, or `undefined` on a complete miss. */
	data: T | undefined;
	/** `true` when served from cache (the live fetch was skipped or failed). */
	stale: boolean;
	/**
	 * Epoch millis of when the returned copy was persisted. Present for fresh data
	 * (just now) and for cached copies written after the envelope migration;
	 * `undefined` for a complete miss or a legacy entry.
	 */
	cachedAt?: number;
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
		const cached = await readEnvelope<T>(key);
		return { data: cached?.value, cachedAt: cached?.cachedAt, stale: true };
	}

	try {
		const value = await fetcher({ signal: timeoutSignal(timeoutMs) });
		// Resolved → the server responded, even if the payload was unusable.
		markReachable(true);

		if (value === undefined) {
			// Reachable but errored/empty — prefer the cached copy over a hard failure.
			const cached = await readEnvelope<T>(key);
			return { data: cached?.value, cachedAt: cached?.cachedAt, stale: true };
		}

		const cachedAt = Date.now();
		void writeCache<CachedEnvelope<T>>(key, { value, cachedAt });
		return { data: value, cachedAt, stale: false };
	} catch {
		// Network failure / timeout: serve the last synced copy.
		markReachable(false);
		const cached = await readEnvelope<T>(key);
		return { data: cached?.value, cachedAt: cached?.cachedAt, stale: true };
	}
}

/** Options for {@link warmCache}. */
export interface WarmCacheOptions<T> {
	/** IndexedDB key; must match the key the page's `load` reads (per-user). */
	key: string;
	/** Runs the network request; return the value to cache, or `undefined` to skip. */
	fetcher: (ctx: { signal: AbortSignal }) => Promise<T | undefined>;
	/** Fetch timeout budget; defaults to {@link FIRST_PAINT_TIMEOUT_MS}. */
	timeoutMs?: number;
}

/**
 * Proactively populate a cache entry for a page the user hasn't opened yet, so it
 * is viewable offline from the first run (e.g. warming the schedule on boot).
 *
 * Fire-and-forget: callers must not `await` it inside a `load`, so it never blocks
 * first paint. It is a no-op when the server is unreachable or an entry already
 * exists — once warmed, the normal `load` + SSE refresh keep it fresh, so this
 * never refetches on its own. Swallows every error (offline / timeout / storage).
 */
export async function warmCache<T>({
	key,
	fetcher,
	timeoutMs = FIRST_PAINT_TIMEOUT_MS
}: WarmCacheOptions<T>): Promise<void> {
	try {
		if (!isReachable()) return;
		// Already cached: leave refresh to the page's own load and SSE updates.
		if ((await readCache<unknown>(key)) !== undefined) return;

		const value = await fetcher({ signal: timeoutSignal(timeoutMs) });
		markReachable(true);
		if (value === undefined) return;

		void writeCache<CachedEnvelope<T>>(key, { value, cachedAt: Date.now() });
	} catch {
		// Best-effort warm — ignore failures.
	}
}
