<script lang="ts">
	import { listFeedbackInfiniteOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
	import { offsetPagination } from '$lib/api/queries';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LoadMoreButton from '$lib/components/LoadMoreButton.svelte';
	import { FEEDBACK_PAGE_SIZE } from '$lib/constants/feedback';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { createInfiniteQuery } from '@tanstack/svelte-query';

	import FeedbackCard from './FeedbackCard.svelte';

	const toastService = getToastService();

	const feedQuery = createInfiniteQuery(() => ({
		...listFeedbackInfiniteOptions({ query: { limit: FEEDBACK_PAGE_SIZE } }),
		...offsetPagination(FEEDBACK_PAGE_SIZE, 'feedback')
	}));

	let feedback = $derived(feedQuery.data?.pages.flatMap((page) => page.feedback) ?? []);

	$effect(() => {
		if (feedQuery.isError) {
			toastService.error('Не удалось загрузить отзывы');
		}
	});
</script>

{#if feedback.length === 0}
	<EmptyState message="Отзывов пока нет" />
{:else}
	<div class="flex flex-col gap-3">
		{#each feedback as item (item.id)}
			<FeedbackCard feedback={item} />
		{/each}
	</div>

	{#if feedQuery.hasNextPage}
		<LoadMoreButton
			loading={feedQuery.isFetchingNextPage}
			onclick={() => feedQuery.fetchNextPage()}
		/>
	{/if}
{/if}
