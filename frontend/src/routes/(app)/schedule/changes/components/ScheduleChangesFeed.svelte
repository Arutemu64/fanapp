<script lang="ts">
	import { listScheduleChangesInfiniteOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
	import { offsetPagination } from '$lib/api/queries';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LoadMoreButton from '$lib/components/LoadMoreButton.svelte';
	import { SCHEDULE_CHANGES_PAGE_SIZE } from '$lib/constants/schedule_changes';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { createInfiniteQuery } from '@tanstack/svelte-query';

	import ScheduleChangeCard from './ScheduleChangeCard.svelte';

	const toastService = getToastService();

	const feedQuery = createInfiniteQuery(() => ({
		...listScheduleChangesInfiniteOptions({ query: { limit: SCHEDULE_CHANGES_PAGE_SIZE } }),
		...offsetPagination(SCHEDULE_CHANGES_PAGE_SIZE, 'schedule_changes')
	}));

	let changes = $derived(feedQuery.data?.pages.flatMap((page) => page.schedule_changes) ?? []);

	$effect(() => {
		if (feedQuery.isError) {
			toastService.error('Не удалось загрузить изменения программы');
		}
	});
</script>

{#if changes.length === 0}
	<EmptyState message="Изменений пока нет" />
{:else}
	<div class="flex flex-col gap-3">
		{#each changes as change (change.id)}
			<ScheduleChangeCard {change} />
		{/each}
	</div>

	{#if feedQuery.hasNextPage}
		<LoadMoreButton
			loading={feedQuery.isFetchingNextPage}
			onclick={() => feedQuery.fetchNextPage()}
		/>
	{/if}
{/if}
