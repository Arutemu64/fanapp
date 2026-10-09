import { beforeEach, describe, expect, it, vi } from 'vitest';

// idb-keyval is backed by a plain Map so the epoch guard can be exercised without a
// real IndexedDB (the Vitest runner is Node with no DOM, ADR-0011). The store arg
// each call passes is ignored — there is a single logical store here.
const store = vi.hoisted(() => new Map<string, unknown>());

vi.mock('idb-keyval', () => ({
	createStore: () => ({}),
	get: (key: string) => Promise.resolve(store.get(key)),
	set: (key: string, value: unknown) => Promise.resolve(void store.set(key, value)),
	keys: () => Promise.resolve([...store.keys()]),
	delMany: (ks: string[]) => Promise.resolve(void ks.forEach((k) => store.delete(k)))
}));

// Reachability is switchable per test; it defaults to reachable so fetchWithCache and
// warmCache take the live-fetch path.
const reachability = vi.hoisted(() => ({ reachable: true }));

vi.mock('#lib/services/reachability.js', () => ({
	isReachable: () => reachability.reachable
}));

import { clearUserCache, fetchWithCache, universalScope, userScope } from './offlineCache';

beforeEach(() => {
	store.clear();
	reachability.reachable = true;
});

// A deferred promise lets a test hold a fetch open across a clearUserCache() call,
// reproducing the logout-while-a-request-is-in-flight race.
function deferred<T>() {
	let resolve!: (value: T) => void;
	const promise = new Promise<T>((r) => {
		resolve = r;
	});
	return { promise, resolve };
}

describe('offlineCache epoch guard', () => {
	it('drops a user-scoped write whose fetch began before clearUserCache', async () => {
		const gate = deferred<string>();
		const result = fetchWithCache<string>({
			key: 'subscriptions',
			scope: userScope,
			fetcher: () => gate.promise
		});

		// Logout lands while the request is still in flight.
		await clearUserCache();
		gate.resolve('account-a');

		// The caller still gets the fresh value, but it must not be persisted — otherwise
		// the offline / failed-fetch fallback would serve it to the next account.
		expect((await result).data).toBe('account-a');
		expect(store.has('u:subscriptions')).toBe(false);
	});

	it('persists a user-scoped write when no clear intervenes', async () => {
		const result = await fetchWithCache<string>({
			key: 'subscriptions',
			scope: userScope,
			fetcher: () => Promise.resolve('account-a')
		});

		expect(result.data).toBe('account-a');
		// writeCache is fire-and-forget; wait for the async set to land.
		await vi.waitFor(() => expect(store.get('u:subscriptions')).toBeDefined());
	});

	it('does not gate universal writes across a clear', async () => {
		const gate = deferred<string>();
		const result = fetchWithCache<string>({
			key: 'schedule',
			scope: universalScope,
			fetcher: () => gate.promise
		});

		await clearUserCache();
		gate.resolve('public-schedule');
		await result;

		// Universal data carries no identity, so a clear never invalidates its write.
		await vi.waitFor(() => expect(store.get('g:schedule')).toBeDefined());
	});
});

describe('offlineCache fallback', () => {
	const failing = () => Promise.reject(new Error('network down'));

	it('serves the cached copy without calling the fetcher when unreachable', async () => {
		store.set('u:subscriptions', { value: 'cached', cachedAt: 1000 });
		reachability.reachable = false;
		const fetcher = vi.fn(() => Promise.resolve('fresh'));

		const result = await fetchWithCache<string>({
			key: 'subscriptions',
			scope: userScope,
			fetcher
		});

		expect(fetcher).not.toHaveBeenCalled();
		expect(result).toEqual({ data: 'cached', cachedAt: 1000, stale: true });
	});

	it('falls back to the cache when the fetch throws', async () => {
		store.set('g:schedule', { value: 'cached', cachedAt: 2000 });

		const result = await fetchWithCache<string>({
			key: 'schedule',
			scope: universalScope,
			fetcher: failing
		});

		expect(result).toEqual({ data: 'cached', cachedAt: 2000, stale: true });
	});

	it('falls back to the cache when the fetcher reports no usable data', async () => {
		store.set('g:schedule', { value: 'cached', cachedAt: 3000 });

		const result = await fetchWithCache<string>({
			key: 'schedule',
			scope: universalScope,
			fetcher: () => Promise.resolve(undefined)
		});

		expect(result).toEqual({ data: 'cached', cachedAt: 3000, stale: true });
	});

	it('returns a stale miss when nothing is cached', async () => {
		const result = await fetchWithCache<string>({
			key: 'schedule',
			scope: universalScope,
			fetcher: failing
		});

		expect(result).toEqual({ data: undefined, cachedAt: undefined, stale: true });
	});

	it('serves a legacy bare value without a timestamp', async () => {
		store.set('g:schedule', 'legacy');
		reachability.reachable = false;

		const result = await fetchWithCache<string>({
			key: 'schedule',
			scope: universalScope,
			fetcher: failing
		});

		expect(result).toEqual({ data: 'legacy', cachedAt: undefined, stale: true });
	});

	it('stamps fresh data with cachedAt and persists the same stamp', async () => {
		vi.useFakeTimers({ toFake: ['Date'] });
		vi.setSystemTime(5000);
		try {
			const result = await fetchWithCache<string>({
				key: 'schedule',
				scope: universalScope,
				fetcher: () => Promise.resolve('fresh')
			});

			expect(result).toEqual({ data: 'fresh', cachedAt: 5000, stale: false });
			await vi.waitFor(() =>
				expect(store.get('g:schedule')).toEqual({ value: 'fresh', cachedAt: 5000 })
			);
		} finally {
			vi.useRealTimers();
		}
	});

	it('scopes entries: a user entry is not served for the universal scope and vice versa', async () => {
		store.set('u:profile', { value: 'user-data', cachedAt: 1 });
		reachability.reachable = false;

		const asUniversal = await fetchWithCache<string>({
			key: 'profile',
			scope: universalScope,
			fetcher: failing
		});
		const asUser = await fetchWithCache<string>({
			key: 'profile',
			scope: userScope,
			fetcher: failing
		});

		expect(asUniversal.data).toBeUndefined();
		expect(asUser.data).toBe('user-data');
	});

	it('clearUserCache drops user entries and keeps universal ones', async () => {
		store.set('u:profile', { value: 'user-data', cachedAt: 1 });
		store.set('g:schedule', { value: 'public', cachedAt: 1 });
		reachability.reachable = false;

		await clearUserCache();

		const user = await fetchWithCache<string>({
			key: 'profile',
			scope: userScope,
			fetcher: failing
		});
		const universal = await fetchWithCache<string>({
			key: 'schedule',
			scope: universalScope,
			fetcher: failing
		});
		expect(user.data).toBeUndefined();
		expect(universal.data).toBe('public');
	});
});
