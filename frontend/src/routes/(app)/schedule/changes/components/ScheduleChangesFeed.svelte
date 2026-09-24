<script lang="ts">
	import type { ScheduleChangeFullDto } from '$lib/api/generated';

	import { createApiClient } from '$lib/api';
	import { listScheduleChanges } from '$lib/api/generated';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LoadMoreButton from '$lib/components/LoadMoreButton.svelte';
	import {
		SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT,
		SCHEDULE_CHANGES_PAGE_SIZE
	} from '$lib/constants/schedule_changes';
	import { PaginatedFeed } from '$lib/services/feed.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';

	import ScheduleChangeCard from './ScheduleChangeCard.svelte';

	interface Props {
		initialChanges: Array<ScheduleChangeFullDto>;
		initialHasMore: boolean;
	}

	let { initialChanges, initialHasMore }: Props = $props();

	const client = createApiClient();
	const toastService = getToastService();

	const feed = new PaginatedFeed<ScheduleChangeFullDto>({
		pageSize: SCHEDULE_CHANGES_PAGE_SIZE,
		requestLimit: SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT,
		getInitialItems: () => initialChanges,
		getInitialHasMore: () => initialHasMore,
		fetchPage: async (limit, offset) => {
			const { data, error } = await listScheduleChanges({
				client,
				query: { limit, offset }
			});
			return error || !data ? null : data.schedule_changes;
		},
		onError: () => toastService.add('Не удалось загрузить изменения программы', 'error')
	});
</script>

{#if feed.items.length === 0}
	<EmptyState message="Изменений пока нет" />
{:else}
	<div class="flex flex-col gap-3">
		{#each feed.items as change (change.id)}
			<ScheduleChangeCard {change} />
		{/each}
	</div>

	{#if feed.hasMore}
		<LoadMoreButton loading={feed.isLoadingMore} onclick={feed.loadMore} />
	{/if}
{/if}
