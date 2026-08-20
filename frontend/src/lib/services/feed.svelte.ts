import { dedupeById } from '$lib/utils/feed';

interface Identified {
	id: number | string;
}

interface PaginatedFeedOptions<T extends Identified> {
	// Page size shown to the user. We over-fetch one extra item to detect a next page.
	pageSize: number;
	requestLimit: number;
	// Getters (not snapshots) so the feed reacts if the server-loaded first page changes.
	getInitialItems: () => ReadonlyArray<T>;
	getInitialHasMore: () => boolean;
	// Fetch one over-fetched page (up to `requestLimit` items). Return the raw list
	// or `null` on a handled API error; throwing is treated the same as `null`.
	fetchPage: (limit: number, offset: number) => Promise<ReadonlyArray<T> | null>;
	// Shown when a fetch fails (handled error or thrown exception).
	onError: () => void;
}

/**
 * Shared "load more" pagination for the notification and schedule-change feeds.
 * The server renders the first page; this holds only the pages loaded afterwards
 * and exposes the combined, deduplicated list plus the load-more action.
 */
export class PaginatedFeed<T extends Identified> {
	#options: PaginatedFeedOptions<T>;

	extraItems = $state.raw<Array<T>>([]);
	isLoadingMore = $state(false);

	// Null until the first "load more"; then it owns the has-more flag.
	#extraHasMore = $state<boolean | null>(null);
	#extraOffset = $state(0);

	constructor(options: PaginatedFeedOptions<T>) {
		this.#options = options;
	}

	get items(): Array<T> {
		return dedupeById(this.#options.getInitialItems(), this.extraItems);
	}

	get hasMore(): boolean {
		return this.#extraHasMore ?? this.#options.getInitialHasMore();
	}

	get nextOffset(): number {
		return this.#options.getInitialItems().length + this.#extraOffset;
	}

	loadMore = async (): Promise<void> => {
		if (!this.hasMore || this.isLoadingMore) {
			return;
		}

		this.isLoadingMore = true;

		try {
			const page = await this.#options.fetchPage(this.#options.requestLimit, this.nextOffset);

			if (page === null) {
				this.#options.onError();
				return;
			}

			const nextItems = page.slice(0, this.#options.pageSize);

			this.extraItems = dedupeById(this.extraItems, nextItems);
			this.#extraHasMore = page.length > this.#options.pageSize;
			this.#extraOffset += nextItems.length;
		} catch (error) {
			console.error('Failed to load more feed items', error);
			this.#options.onError();
		} finally {
			this.isLoadingMore = false;
		}
	};
}
