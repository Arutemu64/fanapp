<script lang="ts">
	import { createInfiniteQuery } from '@tanstack/svelte-query';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import { listScheduleChangesInfiniteOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import ErrorState from '#lib/components/ErrorState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import OfflineUnavailableState from '#lib/components/OfflineUnavailableState.svelte';
	import { SCHEDULE_CHANGES_PAGE_SIZE } from '#lib/constants/scheduleChanges.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	import SectionSpinner from '../../../../components/SectionSpinner.svelte';
	import ScheduleChangeCard from './ScheduleChangeCard.svelte';

	const toastService = getToastService();

	// Staff-only operational feed: it renders whatever is cached and refetches, but
	// is not meant for offline use.
	const changesQuery = createInfiniteQuery(() => ({
		...listScheduleChangesInfiniteOptions({
			query: { limit: SCHEDULE_CHANGES_PAGE_SIZE }
		}),
		// An object page param is request overrides to hey-api, a string the cursor:
		// an empty object asks for the first page.
		initialPageParam: {},
		getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined
	}));

	let changes = $derived(changesQuery.data?.pages.flatMap((page) => page.schedule_changes) ?? []);
	// Offline the query pauses instead of failing, so without this a cold miss
	// would spin forever.
	let offlineMiss = $derived(changesQuery.data === undefined && !reachability.current);

	async function loadMore() {
		const result = await changesQuery.fetchNextPage();
		if (result.isFetchNextPageError) {
			toastService.add(m.schedule_changes_load_failed(), 'error');
		}
	}
</script>

{#if offlineMiss}
	<OfflineUnavailableState
		title={m.schedule_changes_offline_title()}
		message={m.schedule_changes_offline_message()}
	/>
{:else if changesQuery.data === undefined}
	{#if changesQuery.isError}
		<ErrorState
			variant="inline"
			onRetry={() => void changesQuery.refetch()}
			error={{
				status: 500,
				message: getApiErrorDetail(changesQuery.error) ?? m.schedule_changes_load_failed()
			}}
		/>
	{:else}
		<SectionSpinner />
	{/if}
{:else if changes.length === 0}
	<EmptyState message={m.schedule_changes_empty()} />
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
