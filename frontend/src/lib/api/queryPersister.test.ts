import type { PersistedClient } from '@tanstack/svelte-query-persist-client';

import * as Sentry from '@sentry/sveltekit';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { createIdbPersister, QUERY_CACHE_KEY } from './queryPersister';

const SCHEDULE_SCHEMA = 'schedule-v1';

// The build's schema hashes, which a test changes to stand for a deploy.
let currentHashes: Record<string, string> = { getSchedule: SCHEDULE_SCHEMA };

function persister() {
	return createIdbPersister({
		schemaHashOf: (queryKey) => {
			const [{ _id }] = queryKey as [{ _id: string }];
			return currentHashes[_id];
		}
	});
}

function stored(saved: PersistedClient) {
	return { client: saved, schemaHashes: { getSchedule: SCHEDULE_SCHEMA } };
}

// Copies on write and read with structuredClone, as IndexedDB does, so a value
// that only survives JSON (or not at all) shows up here.
const { store, set } = vi.hoisted(() => {
	const store = new Map<string, unknown>();
	return {
		store,
		set: vi.fn((key: string, value: unknown) => {
			store.set(key, structuredClone(value));
			return Promise.resolve();
		})
	};
});
vi.mock('idb-keyval', () => ({
	set,
	get: (key: string) => Promise.resolve(structuredClone(store.get(key))),
	del: (key: string) => Promise.resolve(store.delete(key))
}));
vi.mock('@sentry/sveltekit', () => ({ captureException: vi.fn() }));

function client(timestamp: number, error: Error | null = null): PersistedClient {
	return {
		timestamp,
		buster: '',
		clientState: {
			mutations: [],
			queries: [
				{
					queryKey: [{ _id: 'getSchedule' }],
					queryHash: 'getSchedule',
					dehydratedAt: timestamp,
					state: {
						data: { events: [] },
						dataUpdateCount: 1,
						dataUpdatedAt: timestamp,
						error,
						errorUpdateCount: error ? 1 : 0,
						errorUpdatedAt: error ? timestamp : 0,
						fetchFailureCount: 0,
						fetchFailureReason: null,
						fetchMeta: null,
						isInvalidated: false,
						status: error ? 'error' : 'success',
						fetchStatus: 'idle'
					}
				}
			]
		}
	};
}

describe('createIdbPersister', () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.clearAllMocks();
		store.clear();
		currentHashes = { getSchedule: SCHEDULE_SCHEMA };
	});

	it('writes a burst of saves once, with the latest client', async () => {
		const cache = persister();

		await cache.persistClient(client(1));
		await cache.persistClient(client(2));
		expect(set).not.toHaveBeenCalled();

		vi.advanceTimersByTime(1000);
		expect(set).toHaveBeenCalledExactlyOnceWith(QUERY_CACHE_KEY, stored(client(2)));
	});

	it('writes again for a save after the last write', async () => {
		const cache = persister();

		await cache.persistClient(client(1));
		vi.advanceTimersByTime(1000);
		await cache.persistClient(client(2));
		vi.advanceTimersByTime(1000);

		expect(set).toHaveBeenCalledTimes(2);
		expect(set).toHaveBeenLastCalledWith(QUERY_CACHE_KEY, stored(client(2)));
	});

	it('restores a saved query error as an Error', async () => {
		const cache = persister();

		await cache.persistClient(client(1, new Error('Failed to fetch')));
		vi.advanceTimersByTime(1000);
		const restored = await cache.restoreClient();

		const error = restored?.clientState.queries[0]?.state.error;
		expect(error).toBeInstanceOf(Error);
		expect(error).toHaveProperty('message', 'Failed to fetch');
	});

	it('reports a write that fails', async () => {
		const failure = new DOMException('could not be cloned', 'DataCloneError');
		set.mockRejectedValueOnce(failure);
		const cache = persister();

		await cache.persistClient(client(1));
		await vi.advanceTimersByTimeAsync(1000);

		expect(Sentry.captureException).toHaveBeenCalledExactlyOnceWith(failure, {
			tags: { source: 'query-persister' }
		});
	});

	it('drops a saved query whose response shape changed, and keeps the mutations', async () => {
		const cache = persister();
		const saved = client(1);
		saved.clientState.mutations = [
			{ mutationKey: ['awardQuestPoints'], state: { isPaused: true } as never }
		];

		await cache.persistClient(saved);
		vi.advanceTimersByTime(1000);
		currentHashes = { getSchedule: 'schedule-v2' };
		const restored = await cache.restoreClient();

		expect(restored?.clientState.queries).toEqual([]);
		expect(restored?.clientState.mutations).toHaveLength(1);
	});

	it('keeps a saved query whose response shape is unchanged', async () => {
		const cache = persister();

		await cache.persistClient(client(1));
		vi.advanceTimersByTime(1000);
		currentHashes = { getSchedule: SCHEDULE_SCHEMA, getQuest: 'quest-v2' };
		const restored = await cache.restoreClient();

		expect(restored?.clientState.queries).toHaveLength(1);
	});

	it('restores nothing from an entry saved without schema hashes', async () => {
		store.set(QUERY_CACHE_KEY, client(1));

		expect(await persister().restoreClient()).toBeUndefined();
	});
});
