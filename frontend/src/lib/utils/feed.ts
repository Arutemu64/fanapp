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

/**
 * Concatenate two lists, dropping any item from `next` whose id already appears
 * in `existing`. Guards the feeds against duplicates when the underlying list
 * shifts between paginated requests (or between an SSE push and a page fetch).
 */
export function dedupeById<T extends { id: number | string }>(
	existing: ReadonlyArray<T>,
	next: ReadonlyArray<T>
): Array<T> {
	const existingIds = new Set(existing.map((item) => item.id));
	return [...existing, ...next.filter((item) => !existingIds.has(item.id))];
}
