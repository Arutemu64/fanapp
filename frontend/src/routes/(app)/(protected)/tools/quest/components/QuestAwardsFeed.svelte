<script lang="ts">
	import { createInfiniteQuery } from '@tanstack/svelte-query';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import { listQuestAwardsInfiniteOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import ErrorState from '#lib/components/ErrorState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import * as Card from '#lib/components/ui/card/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	import SectionSpinner from '../../../../components/SectionSpinner.svelte';
	import QuestAwardItem from './QuestAwardItem.svelte';

	interface Props {
		showAwarder: boolean;
	}

	let { showAwarder }: Props = $props();

	const PAGE_SIZE = 20;
	const toastService = getToastService();

	const awardsQuery = createInfiniteQuery(() => ({
		...listQuestAwardsInfiniteOptions({ query: { limit: PAGE_SIZE } }),
		// An object page param is request overrides to hey-api, a string the cursor:
		// an empty object asks for the first page.
		initialPageParam: {},
		getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined
	}));

	let awards = $derived(awardsQuery.data?.pages.flatMap((page) => page.awards) ?? []);

	async function loadMore() {
		const result = await awardsQuery.fetchNextPage();
		if (result.isFetchNextPageError) {
			toastService.add(m.quest_tool_history_failed(), 'error');
		}
	}
</script>

{#if awardsQuery.data === undefined}
	{#if awardsQuery.isError}
		<ErrorState
			variant="inline"
			onRetry={() => void awardsQuery.refetch()}
			error={{
				status: 500,
				message: getApiErrorDetail(awardsQuery.error) ?? m.quest_tool_history_failed()
			}}
		/>
	{:else}
		<SectionSpinner />
	{/if}
{:else if awards.length === 0}
	<EmptyState message={m.quest_tool_history_empty()} />
{:else}
	<Card.Root class="w-full max-w-none gap-0 overflow-hidden rounded-2xl p-0">
		<ul class="divide-y divide-border">
			{#each awards as award (award.id)}
				<QuestAwardItem {award} {showAwarder} />
			{/each}
		</ul>
	</Card.Root>

	{#if awardsQuery.hasNextPage}
		<LoadMoreButton
			loading={awardsQuery.isFetchingNextPage}
			busy={awardsQuery.isFetching}
			onclick={loadMore}
		/>
	{/if}
{/if}
