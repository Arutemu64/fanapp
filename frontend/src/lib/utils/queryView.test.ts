import { describe, expect, it, vi } from 'vitest';

import { type QueryPolicy, type QuerySnapshot, queryView } from './queryView';

const FALLBACK = 'Не удалось загрузить программу';
const timedOut = new DOMException('timed out', 'TimeoutError');

function snapshot(overrides: Partial<QuerySnapshot<string>> = {}): QuerySnapshot<string> {
	return {
		data: undefined,
		error: null,
		isError: false,
		isRefetchError: false,
		fetchStatus: 'idle',
		failureReason: null,
		dataUpdatedAt: 0,
		refetch: vi.fn(() => Promise.resolve()),
		...overrides
	};
}

function kindOf(query: QuerySnapshot<string>, policy: QueryPolicy, reachable: boolean) {
	return queryView(query, { policy, reachable, errorMessage: FALLBACK }).kind;
}

describe('queryView', () => {
	it.each([
		// [case, query, policy, reachable, expected]
		['cold miss offline', snapshot(), 'cached', false, 'offline'],
		['cold miss offline, live', snapshot(), 'live', false, 'offline'],
		['loading', snapshot({ fetchStatus: 'fetching' }), 'cached', true, 'loading'],
		[
			'paused fetch, still reachable',
			snapshot({ fetchStatus: 'paused' }),
			'cached',
			true,
			'loading'
		],
		[
			'unanswered read still retrying',
			snapshot({ fetchStatus: 'fetching', failureReason: timedOut }),
			'cached',
			true,
			'offline'
		],
		[
			'unanswered read still retrying, live',
			snapshot({ fetchStatus: 'fetching', failureReason: timedOut }),
			'live',
			true,
			'offline'
		],
		[
			'retries exhausted with the server reachable',
			snapshot({ isError: true, error: timedOut, failureReason: timedOut }),
			'cached',
			true,
			'error'
		],
		[
			'API error while retrying is not offline',
			snapshot({ fetchStatus: 'fetching', failureReason: { code: 'INTERNAL' } }),
			'cached',
			true,
			'loading'
		],
		['cached copy offline', snapshot({ data: 'x' }), 'cached', false, 'ready'],
		['copy in memory offline, live', snapshot({ data: 'x' }), 'live', false, 'offline'],
		['copy online, live', snapshot({ data: 'x' }), 'live', true, 'ready']
	] as const)('%s → %s', (_case, query, policy, reachable, expected) => {
		expect(kindOf(query, policy, reachable)).toBe(expected);
	});

	it('marks a cached copy stale offline or after a failed refetch', () => {
		const options = { policy: 'cached', errorMessage: FALLBACK } as const;
		const fresh = queryView(snapshot({ data: 'x', dataUpdatedAt: 42 }), {
			...options,
			reachable: true
		});
		const offline = queryView(snapshot({ data: 'x' }), { ...options, reachable: false });
		const refetchFailed = queryView(snapshot({ data: 'x', isRefetchError: true }), {
			...options,
			reachable: true
		});

		expect(fresh).toEqual({ kind: 'ready', data: 'x', stale: false, cachedAt: 42 });
		expect(offline).toMatchObject({ stale: true });
		expect(refetchFailed).toMatchObject({ stale: true });
	});

	it('words the error from the API, falling back to the screen copy, and retries by refetching', () => {
		const refetch = vi.fn(() => Promise.resolve());
		const options = { policy: 'cached', reachable: true, errorMessage: FALLBACK } as const;

		const known = queryView(
			snapshot({ isError: true, error: { code: 'TICKET_NOT_FOUND' }, refetch }),
			options
		);
		const unknown = queryView(snapshot({ isError: true, error: { code: 'NOPE' } }), options);

		expect(known).toMatchObject({ kind: 'error', message: 'Билет не найден' });
		expect(unknown).toMatchObject({ kind: 'error', message: FALLBACK });

		if (known.kind === 'error') known.retry();
		expect(refetch).toHaveBeenCalledOnce();
	});
});
