<script lang="ts">
	import { createInfiniteQuery } from '@tanstack/svelte-query';

	import type { FeedbackDto } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import { listFeedbackInfiniteOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import ErrorState from '#lib/components/ErrorState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import { FEEDBACK_PAGE_REQUEST_LIMIT, FEEDBACK_PAGE_SIZE } from '#lib/constants/feedback.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { dedupeById } from '#lib/utils/feed.js';

	import SectionSpinner from '../../../../components/SectionSpinner.svelte';
	import FeedbackItem from './FeedbackItem.svelte';

	const toastService = getToastService();

	// Each page over-fetches one item so a short page proves there is no next one.
	const feedbackQuery = createInfiniteQuery(() => ({
		...listFeedbackInfiniteOptions({ query: { limit: FEEDBACK_PAGE_REQUEST_LIMIT } }),
		initialPageParam: 0,
		getNextPageParam: (lastPage, allPages) => {
			if (lastPage.feedback.length <= FEEDBACK_PAGE_SIZE) return undefined;
			return allPages.length * FEEDBACK_PAGE_SIZE;
		}
	}));

	// Items can shift between page requests, so one may arrive twice.
	let feedback = $derived.by(() => {
		let items: FeedbackDto[] = [];
		for (const page of feedbackQuery.data?.pages ?? []) {
			items = dedupeById(items, page.feedback.slice(0, FEEDBACK_PAGE_SIZE));
		}
		return items;
	});

	async function loadMore() {
		const result = await feedbackQuery.fetchNextPage();
		if (result.isFetchNextPageError) {
			toastService.add('Не удалось загрузить отзывы', 'error');
		}
	}
</script>

{#if feedbackQuery.data === undefined}
	{#if feedbackQuery.isError}
		<ErrorState
			variant="inline"
			onRetry={() => void feedbackQuery.refetch()}
			error={{
				status: 500,
				message: getApiErrorDetail(feedbackQuery.error) ?? 'Не удалось загрузить отзывы'
			}}
		/>
	{:else}
		<SectionSpinner />
	{/if}
{:else if feedback.length === 0}
	<EmptyState message="Отзывов пока нет" />
{:else}
	<!-- One divided list, not a card per item: the entries are all the same shape,
	     so a list scans faster and fits more on a phone screen. -->
	<MenuGroup class="divide-y divide-border">
		{#each feedback as item (item.id)}
			<FeedbackItem feedback={item} />
		{/each}
	</MenuGroup>

	{#if feedbackQuery.hasNextPage}
		<LoadMoreButton
			loading={feedbackQuery.isFetchingNextPage}
			busy={feedbackQuery.isFetching}
			onclick={loadMore}
		/>
	{/if}
{/if}
