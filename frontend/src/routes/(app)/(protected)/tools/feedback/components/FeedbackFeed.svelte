<script lang="ts">
	import { feedbackFeedOptions } from '$lib/api/feeds';
	import { flattenPages } from '$lib/api/pagination';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LoadMoreButton from '$lib/components/LoadMoreButton.svelte';
	import { FEEDBACK_PAGE_SIZE } from '$lib/constants/feedback';
	import { createInfiniteQuery } from '@tanstack/svelte-query';

	import FeedbackCard from './FeedbackCard.svelte';

	const feed = createInfiniteQuery(() => feedbackFeedOptions());

	let items = $derived(flattenPages(feed.data?.pages, (page) => page.feedback, FEEDBACK_PAGE_SIZE));
</script>

{#if items.length === 0}
	<EmptyState message="Отзывов пока нет" />
{:else}
	<div class="flex flex-col gap-3">
		{#each items as item (item.id)}
			<FeedbackCard feedback={item} />
		{/each}
	</div>

	{#if feed.hasNextPage}
		<LoadMoreButton loading={feed.isFetchingNextPage} onclick={() => feed.fetchNextPage()} />
	{/if}
{/if}
