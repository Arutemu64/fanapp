/**
 * The subset of a `createQuery` result this module reads. Structural so the
 * helper stays testable with a plain object.
 */
export interface OfflineQuerySource<T> {
	/** Fresh or persisted value; `undefined` until the first success. */
	data: T | undefined;
	/** Epoch millis of the last successful fetch — restored with a persisted query. */
	dataUpdatedAt: number;
	/** The last fetch failed (and was not retried into a success). */
	isError: boolean;
	/** The fetch is held back because the backend is unreachable. */
	isPaused: boolean;
}

/** The offline flags a page renders from — the shape `load` used to return. */
export interface OfflineQueryState {
	/** Epoch millis the shown copy was fetched, for the "synced at" line. */
	cachedAt: number | undefined;
	/** Offline with nothing saved: show the page's own empty state, not a caveat. */
	offlineMiss: boolean;
	/** A saved copy is on screen because the live fetch was skipped or failed. */
	stale: boolean;
}

/**
 * Translate a query into the offline flags the pages already speak
 * (`StaleDataNotice` via `shouldShowStaleNotice`, and the "недоступно офлайн"
 * empty state).
 *
 * A paused query is the offline case: `onlineManager` is bound to our
 * reachability probe (`$lib/query/online.ts`), so TanStack holds the fetch back
 * rather than firing it into a dead network — and whatever the persister restored
 * stays on screen underneath.
 */
export function offlineQueryState<T>(
	query: OfflineQuerySource<T>,
	isOnline: boolean
): OfflineQueryState {
	if (query.data === undefined) {
		return { cachedAt: undefined, offlineMiss: !isOnline, stale: !isOnline };
	}

	return {
		// 0 is TanStack's "never fetched" sentinel, which a restored query never
		// carries — but a hand-seeded one would, and it must not render as 1970.
		cachedAt: query.dataUpdatedAt > 0 ? query.dataUpdatedAt : undefined,
		offlineMiss: false,
		stale: query.isPaused || query.isError
	};
}
