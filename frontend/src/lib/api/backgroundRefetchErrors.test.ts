import { QueryClient, QueryObserver } from '@tanstack/svelte-query';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { watchBackgroundRefetchErrors } from '#lib/api/index.js';

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
	// The real client rejects with the API body, a plain object, not an Error.
	// eslint-disable-next-line @typescript-eslint/prefer-promise-reject-errors
	const queryFn = () => Promise.reject(error);
	const unsubscribe = observed
		? new QueryObserver(queryClient, { queryKey: KEY, queryFn, meta, enabled: false }).subscribe(
				() => {}
			)
		: () => {};

	await queryClient.fetchQuery({ queryKey: KEY, queryFn, meta, staleTime: 0 }).catch(() => {});

	unsubscribe();
	stop();
	queryClient.clear();
	return onFailure;
}

describe('watchBackgroundRefetchErrors', () => {
	afterEach(() => vi.restoreAllMocks());

	it('reports a failed refetch of a query still showing its last data', async () => {
		const onFailure = await failRefetch({ code: 'INTERNAL_ERROR', details: {} });
		expect(onFailure).toHaveBeenCalledOnce();
	});

	it('stays quiet when there is no data on screen — the page shows the error itself', async () => {
		const onFailure = await failRefetch({ code: 'INTERNAL_ERROR', details: {} }, { cached: false });
		expect(onFailure).not.toHaveBeenCalled();
	});

	it('stays quiet for a query nobody is looking at', async () => {
		const onFailure = await failRefetch(
			{ code: 'INTERNAL_ERROR', details: {} },
			{ observed: false }
		);
		expect(onFailure).not.toHaveBeenCalled();
	});

	it('leaves a missing answer to the connection banner', async () => {
		const onFailure = await failRefetch(new TypeError('Failed to fetch'));
		expect(onFailure).not.toHaveBeenCalled();
	});

	it('leaves session expiry to the session handling', async () => {
		const onFailure = await failRefetch({ code: 'USER_NOT_AUTHENTICATED', details: {} });
		expect(onFailure).not.toHaveBeenCalled();
	});

	it('respects a query that opts out', async () => {
		const onFailure = await failRefetch(
			{ code: 'INTERNAL_ERROR', details: {} },
			{ meta: { quietRefetchErrors: true } }
		);
		expect(onFailure).not.toHaveBeenCalled();
	});
});
