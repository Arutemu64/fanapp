<script lang="ts">
	import { tick } from 'svelte';

	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	interface PagedQuery {
		hasNextPage: boolean;
		isFetchingNextPage: boolean;
		isFetching: boolean;
		fetchNextPage: () => Promise<{ isFetchNextPageError: boolean; hasNextPage: boolean }>;
	}

	interface Props {
		query: PagedQuery;
		list: HTMLElement | null | undefined;
		itemSelector?: string;
		errorMessage: string;
	}

	let { query, list, itemSelector = ':scope > *', errorMessage }: Props = $props();
	const toastService = getToastService();

	function items(): HTMLElement[] {
		return Array.from(list?.querySelectorAll<HTMLElement>(itemSelector) ?? []);
	}

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
		if (!target && !result.hasNextPage) {
			target = after.at(-1);
		}
		if (!target) return;

		const focusable = 'a[href], button:not([disabled])';
		const control = target.matches(focusable)
			? target
			: target.querySelector<HTMLElement>(focusable);
		if (control) {
			control.focus();
			return;
		}
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
