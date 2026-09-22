<script lang="ts">
	import type { FeedbackDto } from '$lib/api/generated';

	import { listFeedbackInfiniteOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
	import { flattenPages, offsetPageParams } from '$lib/api/pagination';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LoadMoreButton from '$lib/components/LoadMoreButton.svelte';
	import { FEEDBACK_PAGE_REQUEST_LIMIT, FEEDBACK_PAGE_SIZE } from '$lib/constants/feedback';
	import { createInfiniteQuery } from '@tanstack/svelte-query';

	import FeedbackCard from './FeedbackCard.svelte';

	const feed = createInfiniteQuery(() => ({
		...listFeedbackInfiniteOptions({ query: { limit: FEEDBACK_PAGE_REQUEST_LIMIT } }),
		...offsetPageParams(
			(page: { feedback: Array<FeedbackDto> }) => page.feedback,
			FEEDBACK_PAGE_SIZE
		)
	}));

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
