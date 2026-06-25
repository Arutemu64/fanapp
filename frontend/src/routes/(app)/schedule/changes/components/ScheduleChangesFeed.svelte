<script lang="ts">
	import type { ScheduleChangeFullDTO } from '$lib/types/schedule';

	import { createApiClient } from '$lib/api';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LoadMoreButton from '$lib/components/LoadMoreButton.svelte';
	import {
		SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT,
		SCHEDULE_CHANGES_PAGE_SIZE
	} from '$lib/constants/schedule_changes';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { PaginatedFeed } from '$lib/utils/feed.svelte';

	import ScheduleChangeCard from './ScheduleChangeCard.svelte';

	interface Props {
		initialChanges: Array<ScheduleChangeFullDTO>;
		initialHasMore: boolean;
	}

	let { initialChanges, initialHasMore }: Props = $props();

	const client = createApiClient();
	const toastService = getToastService();

	const feed = new PaginatedFeed<ScheduleChangeFullDTO>({
		pageSize: SCHEDULE_CHANGES_PAGE_SIZE,
		requestLimit: SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT,
		getInitialItems: () => initialChanges,
		getInitialHasMore: () => initialHasMore,
		fetchPage: async (limit, offset) => {
			const { data, error } = await client.GET('/schedule/changes/', {
				params: { query: { limit, offset } }
			});
			return error || !data ? null : data.schedule_changes;
		},
		onError: () => toastService.error('Не удалось загрузить изменения программы')
	});
</script>

{#if feed.items.length === 0}
	<EmptyState message="Изменений пока нет" />
{:else}
	<div class="space-y-3">
		{#each feed.items as change (change.id)}
			<ScheduleChangeCard {change} />
		{/each}
	</div>

	{#if feed.hasMore}
		<LoadMoreButton loading={feed.isLoadingMore} onclick={feed.loadMore} />
	{/if}
{/if}
