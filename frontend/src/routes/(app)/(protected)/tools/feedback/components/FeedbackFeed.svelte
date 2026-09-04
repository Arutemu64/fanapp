<script lang="ts">
	import type { FeedbackDTO } from '$lib/types/feedback';

	import { createApiClient } from '$lib/api';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LoadMoreButton from '$lib/components/LoadMoreButton.svelte';
	import { FEEDBACK_PAGE_REQUEST_LIMIT, FEEDBACK_PAGE_SIZE } from '$lib/constants/feedback';
	import { PaginatedFeed } from '$lib/services/feed.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';

	import FeedbackCard from './FeedbackCard.svelte';

	interface Props {
		initialFeedback: Array<FeedbackDTO>;
		initialHasMore: boolean;
	}

	let { initialFeedback, initialHasMore }: Props = $props();

	const client = createApiClient();
	const toastService = getToastService();

	const feed = new PaginatedFeed<FeedbackDTO>({
		pageSize: FEEDBACK_PAGE_SIZE,
		requestLimit: FEEDBACK_PAGE_REQUEST_LIMIT,
		getInitialItems: () => initialFeedback,
		getInitialHasMore: () => initialHasMore,
		fetchPage: async (limit, offset) => {
			const { data, error } = await client.GET('/feedback/', {
				params: { query: { limit, offset } }
			});
			return error || !data ? null : data.feedback;
		},
		onError: () => toastService.error('Не удалось загрузить отзывы')
	});
</script>

{#if feed.items.length === 0}
	<EmptyState message="Отзывов пока нет" />
{:else}
	<div class="flex flex-col gap-3">
		{#each feed.items as item (item.id)}
			<FeedbackCard feedback={item} />
		{/each}
	</div>

	{#if feed.hasMore}
		<LoadMoreButton loading={feed.isLoadingMore} onclick={feed.loadMore} />
	{/if}
{/if}
