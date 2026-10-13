<script lang="ts">
	import { createInfiniteQuery } from '@tanstack/svelte-query';

	import type { ScheduleChangeFullDto } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import { listScheduleChangesInfiniteOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import ErrorState from '#lib/components/ErrorState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import {
		SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT,
		SCHEDULE_CHANGES_PAGE_SIZE
	} from '#lib/constants/scheduleChanges.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { dedupeById } from '#lib/utils/feed.js';

	import SectionSpinner from '../../../../components/SectionSpinner.svelte';
	import ScheduleChangeCard from './ScheduleChangeCard.svelte';

	const toastService = getToastService();

	// Staff-only operational feed: it renders whatever is cached and refetches, but
	// is not meant for offline use. Each page over-fetches one row so a short page
	// proves there is no next one.
	const changesQuery = createInfiniteQuery(() => ({
		...listScheduleChangesInfiniteOptions({
			query: { limit: SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT }
		}),
		initialPageParam: 0,
		getNextPageParam: (lastPage, allPages) => {
			if (lastPage.schedule_changes.length <= SCHEDULE_CHANGES_PAGE_SIZE) return undefined;
			return allPages.length * SCHEDULE_CHANGES_PAGE_SIZE;
		}
	}));

	// Rows can shift between page requests, so a row may arrive twice.
	let changes = $derived.by(() => {
		let rows: ScheduleChangeFullDto[] = [];
		for (const page of changesQuery.data?.pages ?? []) {
			rows = dedupeById(rows, page.schedule_changes.slice(0, SCHEDULE_CHANGES_PAGE_SIZE));
		}
		return rows;
	});

	async function loadMore() {
		const result = await changesQuery.fetchNextPage();
		if (result.isFetchNextPageError) {
			toastService.add('Не удалось загрузить изменения программы', 'error');
		}
	}
</script>

{#if changesQuery.data === undefined}
	{#if changesQuery.isError}
		<ErrorState
			variant="inline"
			onRetry={() => void changesQuery.refetch()}
			error={{
				status: 500,
				message: getApiErrorDetail(changesQuery.error) ?? 'Не удалось загрузить изменения программы'
			}}
		/>
	{:else}
		<SectionSpinner />
	{/if}
{:else if changes.length === 0}
	<EmptyState message="Изменений пока нет" />
{:else}
	<div class="flex flex-col gap-3">
		{#each changes as change (change.id)}
			<ScheduleChangeCard {change} />
		{/each}
	</div>

	{#if changesQuery.hasNextPage}
		<LoadMoreButton
			loading={changesQuery.isFetchingNextPage}
			busy={changesQuery.isFetching}
			onclick={loadMore}
		/>
	{/if}
{/if}
