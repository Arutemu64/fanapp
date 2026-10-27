import { getApiErrorDetail, isConnectionFailure } from '#lib/api/errors.js';

export type QueryPolicy = 'cached' | 'live';

export type ReadyView<T> = {
	kind: 'ready';
	data: T;
	stale: boolean;
	cachedAt: number;
};

export type QueryView<T> =
	| { kind: 'offline' }
	| { kind: 'loading' }
	| { kind: 'error'; message: string; retry: () => void }
	| ReadyView<T>;

export interface QuerySnapshot<T> {
	data: T | undefined;
	error: unknown;
	isError: boolean;
	isRefetchError: boolean;
	fetchStatus: 'fetching' | 'paused' | 'idle';
	failureReason: unknown;
	dataUpdatedAt: number;
	refetch: () => Promise<unknown>;
}

interface QueryViewOptions {
	policy: QueryPolicy;
	reachable: boolean;
	errorMessage: string;
}

export function queryView<T>(
	query: QuerySnapshot<T>,
	{ policy, reachable, errorMessage }: QueryViewOptions
): QueryView<T> {
	if (policy === 'live' && !reachable) {
		return { kind: 'offline' };
	}

	if (query.data === undefined) {
		const stillRetryingUnanswered =
			query.fetchStatus !== 'idle' && isConnectionFailure(query.failureReason);
		if (!reachable || stillRetryingUnanswered) {
			return { kind: 'offline' };
		}
		if (query.isError) {
			return {
				kind: 'error',
				message: getApiErrorDetail(query.error) ?? errorMessage,
				retry: () => void query.refetch()
			};
		}
		return { kind: 'loading' };
	}

	return {
		kind: 'ready',
		data: query.data,
		stale: query.isRefetchError || !reachable,
		cachedAt: query.dataUpdatedAt
	};
}
