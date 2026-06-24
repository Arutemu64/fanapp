/**
 * Shared helpers for the paginated feeds (notifications, schedule changes).
 */

/**
 * Build a snapshot key from a server-loaded page. Feeding it to a `{#key}` block
 * remounts the feed component with the fresh first page after `invalidate()`.
 */
export function feedSnapshotKey(hasMore: boolean, ids: ReadonlyArray<number | string>): string {
	return `${hasMore}:${ids.join(':')}`;
}
