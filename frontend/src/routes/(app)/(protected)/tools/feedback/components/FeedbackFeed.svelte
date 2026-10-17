<script lang="ts">
	import { createInfiniteQuery } from '@tanstack/svelte-query';

	import { listFeedbackInfiniteOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import QueryState from '#lib/components/QueryState.svelte';
	import { FEEDBACK_PAGE_SIZE } from '#lib/constants/feedback.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { queryView } from '#lib/utils/queryView.js';

	import SectionSpinner from '../../../../components/SectionSpinner.svelte';
	import FeedbackItem from './FeedbackItem.svelte';

	const toastService = getToastService();

	const feedbackQuery = createInfiniteQuery(() => ({
		...listFeedbackInfiniteOptions({ query: { limit: FEEDBACK_PAGE_SIZE } }),
		// An object page param is request overrides to hey-api, a string the cursor:
		// an empty object asks for the first page.
		initialPageParam: {},
		getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined
	}));

	let feedback = $derived(feedbackQuery.data?.pages.flatMap((page) => page.feedback) ?? []);
	let feedbackView = $derived(
		queryView(feedbackQuery, {
			policy: 'cached',
			reachable: reachability.current,
			errorMessage: m.feedback_load_failed()
		})
	);

	async function loadMore() {
		const result = await feedbackQuery.fetchNextPage();
		if (result.isFetchNextPageError) {
			toastService.add(m.feedback_load_failed(), 'error');
		}
	}
</script>

<QueryState view={feedbackView}>
	{#snippet loading()}
		<SectionSpinner />
	{/snippet}

	{#snippet ready()}
		{#if feedback.length === 0}
			<EmptyState message={m.feedback_empty()} />
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
	{/snippet}
</QueryState>
