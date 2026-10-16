import type { PersistedClient } from '@tanstack/svelte-query-persist-client';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { createIdbPersister, QUERY_CACHE_KEY } from './queryPersister';

const { set } = vi.hoisted(() => ({ set: vi.fn(() => Promise.resolve()) }));
vi.mock('idb-keyval', () => ({ set, get: vi.fn(), del: vi.fn(() => Promise.resolve()) }));
vi.mock('@sentry/sveltekit', () => ({ captureException: vi.fn() }));

function client(timestamp: number): PersistedClient {
	return { timestamp, buster: '', clientState: { queries: [], mutations: [] } };
}

describe('createIdbPersister', () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
		set.mockClear();
	});

	it('writes a burst of saves once, with the latest client', async () => {
		const persister = createIdbPersister();

		await persister.persistClient(client(1));
		await persister.persistClient(client(2));
		expect(set).not.toHaveBeenCalled();

		vi.advanceTimersByTime(1000);
		expect(set).toHaveBeenCalledExactlyOnceWith(QUERY_CACHE_KEY, client(2));
	});

	it('writes again for a save after the last write', async () => {
		const persister = createIdbPersister();

		await persister.persistClient(client(1));
		vi.advanceTimersByTime(1000);
		await persister.persistClient(client(2));
		vi.advanceTimersByTime(1000);

		expect(set).toHaveBeenCalledTimes(2);
		expect(set).toHaveBeenLastCalledWith(QUERY_CACHE_KEY, client(2));
	});
});
