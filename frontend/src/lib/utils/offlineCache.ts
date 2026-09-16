import { isReachable, markReachable } from '$lib/services/reachability';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';
import { cacheStore } from '$lib/utils/idbStore';
import { del, delMany, get, keys, set } from 'idb-keyval';

/**
 * IndexedDB persistence for the **identity** load (`/me` in the root layout), so
 * the app can boot offline knowing who is signed in.
 *
 * Page data (schedule, notifications, festival config) is NOT cached here — it
 * lives in the TanStack Query cache, persisted by `$lib/query/persister.ts` into
 * the same database. Identity stays on this path because it is the auth boundary
 * the router is built on: `+layout.ts` must resolve a user before the
 * `(protected)` guard runs, and a `load` cannot reach the QueryClient, which the
 * root layout *component* owns (per-user state never lives in a module).
 *
 * Entries are scoped by key prefix, matching the query cache's persist scopes:
 *
 *   - `'universal'`: data identical for everyone. Survives logout.
 *   - `'user'`: data belonging to the signed-in user. Cleared on logout so it can
 *     never surface for the next account on a shared device.
 *
 * All helpers swallow storage errors (private mode, disabled storage, quota) and
 * degrade to a cache miss / no-op — offline caching is best-effort and must never
 * break a normal online load.
 */

// Monotonic epoch bumped by clearUserCache(). A user-scoped write captures it when
// its fetch begins and is dropped if the epoch has moved before the write lands, so
// an in-flight request that resolves after logout cannot repopulate a cleared entry
// for the next account. Not user/session data — a transient concurrency guard, safe
// as module state in this client-only SPA (cf. the latch in lib/api/index.ts).
let userCacheEpoch = 0;

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

async function readCache<T>(key: string, scope: CacheScope): Promise<T | undefined> {
	try {
		return await get<T>(scopedKey(scope, key), cacheStore);
	} catch {
		return undefined;
	}
}

async function writeCache<T>(
	key: string,
	value: T,
	scope: CacheScope,
	epoch: number
): Promise<void> {
	// Drop a user-scoped write whose originating fetch began before a clearUserCache()
	// (the epoch has since moved): otherwise an in-flight request resolving after logout
	// would repopulate a cleared entry and leak it to the next account. Universal writes
	// carry no identity, so they are never gated.
	if (scope === 'user' && epoch !== userCacheEpoch) return;
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
	// Bump first (synchronously): any user-scoped write already in flight captured the
	// previous epoch and will now be dropped by writeCache, so a response landing after
	// this clear cannot re-create an entry we are about to delete.
	userCacheEpoch += 1;
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
	// Snapshot the user-cache epoch at the start of the operation, so a clearUserCache()
	// that runs while this request is in flight invalidates its eventual write.
	const epoch = userCacheEpoch;

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
		void writeCache<CachedEnvelope<T>>(key, { value, cachedAt }, scope, epoch);
		return { data: value, cachedAt, stale: false };
	} catch {
		// Network failure / timeout: serve the last synced copy.
		markReachable(false);
		const cached = await readEnvelope<T>(key, scope);
		return { data: cached?.value, cachedAt: cached?.cachedAt, stale: true };
	}
}

// Page data that used to be cached here and now lives in the TanStack Query cache
// (`$lib/query/persister.ts`). Installed apps still carry these entries, and
// nothing reads them any more — they would sit in IndexedDB until the visitor
// clears site data.
const RETIRED_KEYS = ['g:schedule', 'g:public-config-v2', 'u:notifications', 'u:subscriptions'];

/**
 * Delete the entries retired by the move to TanStack Query. Fire-and-forget from
 * the root layout on boot; deleting a key that is already gone is a no-op, so
 * this costs one IndexedDB transaction per launch and can be dropped once the
 * installed base has turned over.
 */
export async function dropRetiredCacheEntries(): Promise<void> {
	try {
		await Promise.all(RETIRED_KEYS.map((key) => del(key, cacheStore)));
	} catch {
		// Ignore — storage may be unavailable. Best-effort like the other helpers.
	}
}
