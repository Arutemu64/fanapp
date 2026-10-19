import { getApiErrorDetail, isConnectionFailure } from '#lib/api/errors.js';

/**
 * How a screen treats its read when the server is out of reach.
 *
 * - `cached`: a copy on hand stays on screen offline, flagged stale; only a
 *   complete miss is the offline state.
 * - `live`: never shown offline, not even a copy still in memory — voting, where
 *   a stale open/closed or already-voted state leads to a ballot that can't be
 *   submitted (docs/offline.md "Screens offline").
 */
export type QueryPolicy = 'cached' | 'live';

export type ReadyView<T> = {
	kind: 'ready';
	data: T;
	/** The last refetch failed or the server is out of reach: show a stale notice. */
	stale: boolean;
	/** Epoch millis of when `data` was fetched, for the notice's "synced at" line. */
	cachedAt: number;
};

export type QueryView<T> =
	| { kind: 'offline' }
	| { kind: 'loading' }
	| { kind: 'error'; message: string; retry: () => void }
	| ReadyView<T>;

/** The slice of a TanStack query result (plain or infinite) the view reads. */
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
	/** `reachability.current`, passed in so this stays pure and table-testable. */
	reachable: boolean;
	/** Shown when the API error carries no detail of its own. */
	errorMessage: string;
}

/**
 * Turns one screen read into the single state the screen renders, so the
 * offline/loading/error/stale chain is decided in one place rather than per page.
 *
 * Offline the query pauses instead of failing, so without the offline branch a
 * complete miss would show its skeleton forever. A read that got no answer at all
 * counts as offline too, without waiting for the reachability probe to confirm it
 * or for the retries to run out (`failureReason` is set on the first failed
 * attempt). Only while it is still retrying, though: once the retries stop with
 * the server reachable, nothing reconnects, so the error and its retry button
 * take over.
 *
 * The thrown error is the API body without its HTTP status, so the error view
 * carries a message and no status (see `getApiErrorCode`).
 */
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
