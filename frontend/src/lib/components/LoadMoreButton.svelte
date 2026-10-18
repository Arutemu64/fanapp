<script lang="ts">
	import { tick } from 'svelte';

	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	// The slice of a TanStack infinite query this button drives.
	interface PagedQuery {
		hasNextPage: boolean;
		isFetchingNextPage: boolean;
		// Any fetch of the list is running. A background refetch rewrites every
		// loaded page, and fetching the next one meanwhile can overwrite it
		// (https://tanstack.com/query/latest/docs/framework/react/guides/infinite-queries).
		isFetching: boolean;
		fetchNextPage: () => Promise<{ isFetchNextPageError: boolean; hasNextPage: boolean }>;
	}

	interface Props {
		query: PagedQuery;
		/** The element holding the rendered items. */
		list: HTMLElement | null | undefined;
		/** Matches one element per item inside `list`; its direct children by default. */
		itemSelector?: string;
		/** Toast shown when the next page fails to load. */
		errorMessage: string;
	}

	let { query, list, itemSelector = ':scope > *', errorMessage }: Props = $props();
	const toastService = getToastService();

	function items(): HTMLElement[] {
		return Array.from(list?.querySelectorAll<HTMLElement>(itemSelector) ?? []);
	}

	// Moves focus to the first item of the page just loaded, the usual advice for a
	// load-more control: keyboard and screen-reader users continue where the new
	// content starts, and focus isn't dropped to <body> when the button disables
	// while loading or unmounts after the last page. Keyed {#each} blocks keep
	// the existing items' nodes, so a node not seen before is a new item, wherever
	// a concurrent refetch put it.
	async function loadMore() {
		const before = new Set(items());
		const result = await query.fetchNextPage();
		if (result.isFetchNextPageError) {
			toastService.add(errorMessage, 'error');
			return;
		}

		await tick();
		const after = items();
		let target = after.find((item) => !before.has(item));
		// An empty or all-duplicate last page adds nothing but still removes the
		// button, so hand focus to the end of the list instead.
		if (!target && !result.hasNextPage) {
			target = after.at(-1);
		}
		if (!target) return;

		const control = target.querySelector<HTMLElement>('a[href], button:not([disabled])');
		if (control) {
			control.focus();
			return;
		}
		// An item with nothing focusable inside still takes focus programmatically.
		if (!target.hasAttribute('tabindex')) {
			target.tabIndex = -1;
		}
		target.focus();
	}
</script>

{#if query.hasNextPage}
	<div class="mt-4 flex justify-center">
		<Button
			variant="outline"
			class="w-full sm:w-auto"
			onclick={loadMore}
			disabled={query.isFetching}
		>
			{#if query.isFetchingNextPage}
				<Spinner data-icon="inline-start" />
			{/if}
			{query.isFetchingNextPage ? m.common_loading() : m.common_show_more()}
		</Button>
	</div>
{/if}
