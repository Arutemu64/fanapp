import { InfiniteQueryObserver, QueryClient } from '@tanstack/svelte-query';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { currentUserOptions } from '#lib/services/identity.js';

import { notificationsFeedOptions, warmOfflineCache } from './offlineQueries';

vi.mock('$app/env/public', () => ({ PUBLIC_API_URL: 'https://api.test' }));
vi.mock('#lib/services/reachability.js', () => ({ isReachable: () => true }));

// Answers every request with an empty body, except the feed, which always has a
// next page, so a refetch would walk as many pages as the cache holds. The feed
// answers once `feedGate` settles, to hold a fetch in flight.
function stubApi(feedGate: Promise<unknown> = Promise.resolve()) {
	const fetchMock = vi.fn<typeof fetch>(async (input) => {
		const url = new URL(input instanceof Request ? input.url : String(input), 'https://api.test');
		if (!url.pathname.endsWith('/notifications')) return Response.json({});
		await feedGate;
		return Response.json({ notifications: [], next_cursor: 'next' });
	});
	vi.stubGlobal('fetch', fetchMock);
	return fetchMock;
}

function feedRequests(fetchMock: ReturnType<typeof stubApi>): number {
	return fetchMock.mock.calls.filter(([input]) => {
		const url = input instanceof Request ? input.url : String(input);
		return new URL(url, 'https://api.test').pathname.endsWith('/notifications');
	}).length;
}

// A signed-in viewer whose notifications feed was scrolled three pages deep a
// while ago, so it is stale now.
function clientWithDeepFeed(): QueryClient {
	const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
	queryClient.setQueryData(currentUserOptions().queryKey, { id: 'user' } as never);
	const page = { notifications: [], next_cursor: 'next' };
	queryClient.setQueryData(
		notificationsFeedOptions().queryKey,
		{ pages: [page, page, page], pageParams: [{}, 'c1', 'c2'] },
		{ updatedAt: 0 }
	);
	return queryClient;
}

describe('warmOfflineCache', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('refetches only the first page of a feed nobody is looking at', async () => {
		const fetchMock = stubApi();
		const queryClient = clientWithDeepFeed();

		await warmOfflineCache(queryClient);
		await vi.waitFor(() => expect(queryClient.isFetching()).toBe(0));

		expect(feedRequests(fetchMock)).toBe(1);
		const feed = queryClient.getQueryData(notificationsFeedOptions().queryKey);
		expect(feed?.pages).toHaveLength(1);
		queryClient.clear();
	});

	it('never shortens the list under a reader who opens the feed mid-warm', async () => {
		const { promise: feedGate, resolve: answerFeed } = Promise.withResolvers<undefined>();
		const fetchMock = stubApi(feedGate);
		const queryClient = clientWithDeepFeed();

		await warmOfflineCache(queryClient);
		await vi.waitFor(() => expect(feedRequests(fetchMock)).toBe(1));

		// The reader arrives while the first-page fetch is still on its way.
		const shown: number[] = [];
		const observer = new InfiniteQueryObserver(queryClient, {
			...notificationsFeedOptions(),
			enabled: false
		});
		shown.push(observer.getCurrentResult().data?.pages.length ?? 0);
		const unsubscribe = observer.subscribe((result) => {
			shown.push(result.data?.pages.length ?? 0);
		});

		answerFeed(undefined);
		await vi.waitFor(() => expect(queryClient.isFetching()).toBe(0));

		expect(shown.at(0)).toBe(1);
		expect(shown.every((length) => length >= 1)).toBe(true);
		expect(Math.min(...shown)).toBe(Math.max(...shown));
		unsubscribe();
		queryClient.clear();
	});

	it('refetches every page of a feed on screen, so the list stays as long', async () => {
		const fetchMock = stubApi();
		const queryClient = clientWithDeepFeed();
		const unsubscribe = new InfiniteQueryObserver(queryClient, {
			...notificationsFeedOptions(),
			enabled: false
		}).subscribe(() => {});

		await warmOfflineCache(queryClient);
		await vi.waitFor(() => expect(queryClient.isFetching()).toBe(0));

		expect(feedRequests(fetchMock)).toBe(3);

		const feed = queryClient.getQueryData(notificationsFeedOptions().queryKey);
		expect(feed?.pages).toHaveLength(3);
		unsubscribe();
		queryClient.clear();
	});
});
