import { InfiniteQueryObserver, QueryClient, QueryObserver } from '@tanstack/svelte-query';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { watchBackgroundRefetchErrors } from '#lib/api/index.js';
import { droppedConnectionError } from '#lib/testing/connection.js';

const KEY = ['thing'];

// A query on screen (one observer) that has already loaded once, whose next
// fetch rejects with `error`.
async function failRefetch(
	error: unknown,
	options: { cached?: boolean; observed?: boolean; meta?: Record<string, unknown> } = {}
) {
	const { cached = true, observed = true, meta } = options;
	const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
	if (cached) queryClient.setQueryData(KEY, 'last good');

	const onFailure = vi.fn();
	const stop = watchBackgroundRefetchErrors(queryClient, onFailure);
	// eslint-disable-next-line @typescript-eslint/prefer-promise-reject-errors -- the real client rejects with the API body, a plain object, not an Error
	const queryFn = () => Promise.reject(error);
	const unsubscribe = observed
		? new QueryObserver(queryClient, { queryKey: KEY, queryFn, meta, enabled: false }).subscribe(
				() => {}
			)
		: () => {};

	await queryClient.query({ queryKey: KEY, queryFn, meta, staleTime: 0 }).catch(() => {});

	unsubscribe();
	stop();
	queryClient.clear();
	return onFailure;
}

describe('watchBackgroundRefetchErrors', () => {
	afterEach(() => vi.restoreAllMocks());

	it('reports a failed refetch of a query still showing its last data', async () => {
		const onFailure = await failRefetch({ code: 'INTERNAL_ERROR' });
		expect(onFailure).toHaveBeenCalledOnce();
	});

	it('stays quiet when there is no data on screen — the page shows the error itself', async () => {
		const onFailure = await failRefetch({ code: 'INTERNAL_ERROR' }, { cached: false });
		expect(onFailure).not.toHaveBeenCalled();
	});

	it('stays quiet for a query nobody is looking at', async () => {
		const onFailure = await failRefetch({ code: 'INTERNAL_ERROR' }, { observed: false });
		expect(onFailure).not.toHaveBeenCalled();
	});

	it('leaves a missing answer to the connection banner', async () => {
		const onFailure = await failRefetch(await droppedConnectionError());
		expect(onFailure).not.toHaveBeenCalled();
	});

	it('leaves session expiry to the session handling', async () => {
		const onFailure = await failRefetch({ code: 'USER_NOT_AUTHENTICATED' });
		expect(onFailure).not.toHaveBeenCalled();
	});

	it('respects a query that opts out', async () => {
		const onFailure = await failRefetch(
			{ code: 'INTERNAL_ERROR' },
			{ meta: { quietRefetchErrors: true } }
		);
		expect(onFailure).not.toHaveBeenCalled();
	});

	describe('a paginated feed', () => {
		// A feed on screen with its first page loaded; every later request fails.
		async function loadedFeed() {
			const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
			const onFailure = vi.fn();
			const stop = watchBackgroundRefetchErrors(queryClient, onFailure);
			let failing = false;
			const observer = new InfiniteQueryObserver(queryClient, {
				queryKey: ['feed'],
				queryFn: ({ pageParam }) => {
					if (!failing) return Promise.resolve(pageParam);
					// eslint-disable-next-line @typescript-eslint/prefer-promise-reject-errors -- an API error body, as the real client rejects with
					return Promise.reject({ code: 'INTERNAL_ERROR' });
				},
				initialPageParam: 0,
				getNextPageParam: (lastPage: number) => lastPage + 1
			});
			const unsubscribe = observer.subscribe(() => {});
			await observer.refetch();
			failing = true;
			const teardown = () => {
				unsubscribe();
				stop();
				queryClient.clear();
			};
			return { observer, onFailure, teardown };
		}

		it('leaves a failed «Показать ещё» to the feed, which shows its own error', async () => {
			const { observer, onFailure, teardown } = await loadedFeed();
			const result = await observer.fetchNextPage();
			teardown();
			expect(result.isFetchNextPageError).toBe(true);
			expect(onFailure).not.toHaveBeenCalled();
		});

		it('still reports a failed refresh of the loaded pages', async () => {
			const { observer, onFailure, teardown } = await loadedFeed();
			await observer.refetch();
			teardown();
			expect(onFailure).toHaveBeenCalledOnce();
		});
	});
});
