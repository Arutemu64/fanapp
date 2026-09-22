<script lang="ts">
	import { scheduleChangesFeedOptions } from '$lib/api/feeds';
	import { flattenPages } from '$lib/api/pagination';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LoadMoreButton from '$lib/components/LoadMoreButton.svelte';
	import { SCHEDULE_CHANGES_PAGE_SIZE } from '$lib/constants/schedule_changes';
	import { createInfiniteQuery } from '@tanstack/svelte-query';

	import ScheduleChangeCard from './ScheduleChangeCard.svelte';

	const feed = createInfiniteQuery(() => scheduleChangesFeedOptions());

	let changes = $derived(
		flattenPages(feed.data?.pages, (page) => page.schedule_changes, SCHEDULE_CHANGES_PAGE_SIZE)
	);
</script>

{#if changes.length === 0}
	<EmptyState message="Изменений пока нет" />
{:else}
	<div class="flex flex-col gap-3">
		{#each changes as change (change.id)}
			<ScheduleChangeCard {change} />
		{/each}
	</div>

	{#if feed.hasNextPage}
		<LoadMoreButton loading={feed.isFetchingNextPage} onclick={() => feed.fetchNextPage()} />
	{/if}
{/if}
