/**
 * Shared helpers for the paginated feeds (notifications, schedule changes,
 * broadcasts, feedback).
 */

/**
 * Concatenate two lists, dropping any item from `next` whose id already appears
 * in `existing`. Guards the feeds against duplicates when the underlying list
 * shifts between paginated requests.
 */
export function dedupeById<T extends { id: number | string }>(
	existing: ReadonlyArray<T>,
	next: ReadonlyArray<T>
): Array<T> {
	const existingIds = new Set(existing.map((item) => item.id));
	return [...existing, ...next.filter((item) => !existingIds.has(item.id))];
}
