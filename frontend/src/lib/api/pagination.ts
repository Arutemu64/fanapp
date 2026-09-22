/**
 * Page params for the list endpoints that paginate by `offset` and return no
 * total.
 *
 * Each request over-fetches one item past the page size, and that extra item is
 * the only signal that a next page exists — hence `pageSize + 1` as the request
 * limit everywhere. Callers render `pageSize` items per page and let this decide
 * `hasNextPage`.
 */
export function offsetPageParams<TPage>(
	items: (page: TPage) => ReadonlyArray<unknown>,
	pageSize: number
) {
	return {
		getNextPageParam: (lastPage: TPage, allPages: Array<TPage>): number | undefined => {
			if (items(lastPage).length <= pageSize) return undefined;
			return allPages.length * pageSize;
		},
		initialPageParam: 0
	};
}

/** Flatten loaded pages into the list to render, dropping each page's probe item. */
export function flattenPages<TPage, TItem>(
	pages: ReadonlyArray<TPage> | undefined,
	items: (page: TPage) => ReadonlyArray<TItem>,
	pageSize: number
): Array<TItem> {
	return (pages ?? []).flatMap((page) => items(page).slice(0, pageSize));
}
