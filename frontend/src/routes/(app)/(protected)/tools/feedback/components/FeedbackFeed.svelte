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
	import { queryView } from '#lib/utils/queryView.js';

	import SectionSpinner from '../../../../components/SectionSpinner.svelte';
	import FeedbackItem from './FeedbackItem.svelte';

	const feedbackQuery = createInfiniteQuery(() => ({
		...listFeedbackInfiniteOptions({ query: { limit: FEEDBACK_PAGE_SIZE } }),
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

	let listElement = $state<HTMLElement | null>(null);
</script>

<QueryState view={feedbackView}>
	{#snippet loading()}
		<SectionSpinner />
	{/snippet}

	{#snippet ready()}
		{#if feedback.length === 0}
			<EmptyState message={m.feedback_empty()} />
		{:else}
			<MenuGroup class="divide-y divide-border" bind:ref={listElement}>
				{#each feedback as item (item.id)}
					<FeedbackItem feedback={item} />
				{/each}
			</MenuGroup>

			<LoadMoreButton
				query={feedbackQuery}
				list={listElement}
				errorMessage={m.feedback_load_failed()}
			/>
		{/if}
	{/snippet}
</QueryState>
