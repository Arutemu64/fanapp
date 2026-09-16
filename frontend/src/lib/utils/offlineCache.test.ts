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

// The server is always reachable, so fetchWithCache/warmCache take the live-fetch path.
vi.mock('$lib/services/reachability', () => ({
	isReachable: () => true,
	markReachable: () => {}
}));

import { clearUserCache, fetchWithCache, universalScope, userScope } from './offlineCache';

beforeEach(() => {
	store.clear();
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
