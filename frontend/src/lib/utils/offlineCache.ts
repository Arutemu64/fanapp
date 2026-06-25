import { isReachable, markReachable } from '$lib/services/reachability';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';
import { createStore, delMany, get, keys, set, type UseStore } from 'idb-keyval';

/**
 * Thin wrappers over IndexedDB (via idb-keyval) for persisting the last good
 * copy of read-only API data, so pages can serve it when the network is down.
 *
 * Everything lives in ONE IndexedDB database with ONE object store. Data is
 * scoped by a key prefix rather than by a separate store/database:
 *
 *   - `'universal'`: data identical for everyone (e.g. the public schedule).
 *     Survives logout and is reused by guests and the next account.
 *   - `'user'`: data belonging to the signed-in user (identity, subscriptions,
 *     notifications, connections). Cleared on logout so it can never surface for
 *     the next account on a shared device.
 *
 * Why one database, not two: opening two idb-keyval databases concurrently (each
 * triggering its own first-time upgrade) races in Firefox — it loses the upgrade
 * on the second database, leaving it permanently unusable so every write throws
 * and is silently swallowed. A single database has a single open/upgrade, so
 * there is no race. See idb-keyval issue #32.
 *
 * All helpers swallow storage errors (private mode, disabled storage, quota) and
 * degrade to a cache miss / no-op — offline caching is best-effort and must never
 * break a normal online load.
 */

const cacheStore: UseStore = createStore('fanfan-cache', 'keyval');

/** Scope a cache entry: per-user data is wiped on logout; universal data survives. */
export type CacheScope = 'user' | 'universal';

export const userScope: CacheScope = 'user';
export const universalScope: CacheScope = 'universal';

// Per-user keys carry this prefix so {@link clearUserCache} can find and drop
// exactly them on logout, leaving universal entries untouched.
const USER_KEY_PREFIX = 'u:';
const UNIVERSAL_KEY_PREFIX = 'g:';

function scopedKey(scope: CacheScope, key: string): string {
	return `${scope === 'user' ? USER_KEY_PREFIX : UNIVERSAL_KEY_PREFIX}${key}`;
}

export async function readCache<T>(key: string, scope: CacheScope): Promise<T | undefined> {
	try {
		return await get<T>(scopedKey(scope, key), cacheStore);
	} catch {
		return undefined;
	}
}

export async function writeCache<T>(key: string, value: T, scope: CacheScope): Promise<void> {
	try {
		await set(scopedKey(scope, key), value, cacheStore);
	} catch {
		// Ignore — storage may be unavailable or full.
	}
}

/**
 * Drop every per-user entry on logout / session loss so the next account never
 * reads the previous user's data (e.g. their schedule subscriptions) on a shared
 * device. Universal entries (e.g. the public schedule) are left untouched so they
 * survive a logout and serve the next viewer. Deletes exactly the keys carrying
 * the user prefix. Swallows storage errors like the other helpers.
 */
export async function clearUserCache(): Promise<void> {
	try {
		const allKeys = await keys(cacheStore);
		const userKeys = allKeys.filter(
			(key): key is string => typeof key === 'string' && key.startsWith(USER_KEY_PREFIX)
		);
		if (userKeys.length > 0) {
			await delMany(userKeys, cacheStore);
		}
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
async function readEnvelope<T>(
	key: string,
	scope: CacheScope
): Promise<{ value: T; cachedAt?: number } | undefined> {
	const raw = await readCache<unknown>(key, scope);
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
	/** Cache key within {@link scope}. */
	key: string;
	/** Whether this entry is per-user ({@link userScope}) or shared ({@link universalScope}). */
	scope: CacheScope;
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
	scope,
	fetcher,
	timeoutMs = FIRST_PAINT_TIMEOUT_MS
}: FetchWithCacheOptions<T>): Promise<FetchWithCacheResult<T>> {
	// Known unreachable: serve the cached copy without a dead network wait.
	if (!isReachable()) {
		const cached = await readEnvelope<T>(key, scope);
		return { data: cached?.value, cachedAt: cached?.cachedAt, stale: true };
	}

	try {
		const value = await fetcher({ signal: timeoutSignal(timeoutMs) });
		// Resolved → the server responded, even if the payload was unusable.
		markReachable(true);

		if (value === undefined) {
			// Reachable but errored/empty — prefer the cached copy over a hard failure.
			const cached = await readEnvelope<T>(key, scope);
			return { data: cached?.value, cachedAt: cached?.cachedAt, stale: true };
		}

		const cachedAt = Date.now();
		void writeCache<CachedEnvelope<T>>(key, { value, cachedAt }, scope);
		return { data: value, cachedAt, stale: false };
	} catch {
		// Network failure / timeout: serve the last synced copy.
		markReachable(false);
		const cached = await readEnvelope<T>(key, scope);
		return { data: cached?.value, cachedAt: cached?.cachedAt, stale: true };
	}
}

/** Options for {@link warmCache}. */
export interface WarmCacheOptions<T> {
	/** Cache key; must match the key (and scope) the page's `load` reads. */
	key: string;
	/** Whether this entry is per-user ({@link userScope}) or shared ({@link universalScope}). */
	scope: CacheScope;
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
	scope,
	fetcher,
	timeoutMs = FIRST_PAINT_TIMEOUT_MS
}: WarmCacheOptions<T>): Promise<void> {
	try {
		if (!isReachable()) return;
		// Already cached: leave refresh to the page's own load and SSE updates.
		if ((await readCache<unknown>(key, scope)) !== undefined) return;

		const value = await fetcher({ signal: timeoutSignal(timeoutMs) });
		markReachable(true);
		if (value === undefined) return;

		void writeCache<CachedEnvelope<T>>(key, { value, cachedAt: Date.now() }, scope);
	} catch {
		// Best-effort warm — ignore failures.
	}
}
