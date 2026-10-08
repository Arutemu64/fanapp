<script lang="ts">
	import type { FeedbackDto } from '#lib/api/generated/index.js';

	import { listFeedback } from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import { FEEDBACK_PAGE_REQUEST_LIMIT, FEEDBACK_PAGE_SIZE } from '#lib/constants/feedback.js';
	import { PaginatedFeed } from '#lib/services/feed.svelte.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	import FeedbackItem from './FeedbackItem.svelte';

	interface Props {
		initialFeedback: Array<FeedbackDto>;
		initialHasMore: boolean;
	}

	let { initialFeedback, initialHasMore }: Props = $props();

	const client = createApiClient();
	const toastService = getToastService();

	const feed = new PaginatedFeed<FeedbackDto>({
		pageSize: FEEDBACK_PAGE_SIZE,
		requestLimit: FEEDBACK_PAGE_REQUEST_LIMIT,
		getInitialItems: () => initialFeedback,
		getInitialHasMore: () => initialHasMore,
		fetchPage: async (limit, offset) => {
			const { data, error } = await listFeedback({
				client,
				query: { limit, offset }
			});
			return error || !data ? null : data.feedback;
		},
		onError: () => toastService.add('Не удалось загрузить отзывы', 'error')
	});
</script>

{#if feed.items.length === 0}
	<EmptyState message="Отзывов пока нет" />
{:else}
	<!-- One divided list, not a card per item: the entries are all the same shape,
	     so a list scans faster and fits more on a phone screen. -->
	<MenuGroup class="divide-y divide-border">
		{#each feed.items as item (item.id)}
			<FeedbackItem feedback={item} />
		{/each}
	</MenuGroup>

	{#if feed.hasMore}
		<LoadMoreButton loading={feed.isLoadingMore} onclick={feed.loadMore} />
	{/if}
{/if}
