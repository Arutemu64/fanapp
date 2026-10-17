<script lang="ts">
	import { createInfiniteQuery } from '@tanstack/svelte-query';

	import { listScheduleChangesInfiniteOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import QueryState from '#lib/components/QueryState.svelte';
	import { SCHEDULE_CHANGES_PAGE_SIZE } from '#lib/constants/scheduleChanges.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { queryView } from '#lib/utils/queryView.js';

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
	let changesView = $derived(
		queryView(changesQuery, {
			policy: 'cached',
			reachable: reachability.current,
			errorMessage: m.schedule_changes_load_failed()
		})
	);

	async function loadMore() {
		const result = await changesQuery.fetchNextPage();
		if (result.isFetchNextPageError) {
			toastService.add(m.schedule_changes_load_failed(), 'error');
		}
	}
</script>

<QueryState view={changesView}>
	{#snippet loading()}
		<SectionSpinner />
	{/snippet}

	{#snippet ready()}
		{#if changes.length === 0}
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
	{/snippet}
</QueryState>
