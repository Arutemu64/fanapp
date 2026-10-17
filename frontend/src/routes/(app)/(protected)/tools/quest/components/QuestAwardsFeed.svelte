<script lang="ts">
	import { createInfiniteQuery, createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { QuestAwardItemDto } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		cancelQuestAwardMutation,
		listQuestAwardsInfiniteOptions,
		listQuestAwardsQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import QueryState from '#lib/components/QueryState.svelte';
	import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { queryView } from '#lib/utils/queryView.js';

	import SectionSpinner from '../../../../components/SectionSpinner.svelte';
	import QuestAwardItem from './QuestAwardItem.svelte';

	interface Props {
		showAwarder: boolean;
	}

	let { showAwarder }: Props = $props();

	const PAGE_SIZE = 20;
	const toastService = getToastService();
	const queryClient = useQueryClient();

	const awardsQuery = createInfiniteQuery(() => ({
		...listQuestAwardsInfiniteOptions({ query: { limit: PAGE_SIZE } }),
		// An object page param is request overrides to hey-api, a string the cursor:
		// an empty object asks for the first page.
		initialPageParam: {},
		getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined
	}));

	let awards = $derived(awardsQuery.data?.pages.flatMap((page) => page.awards) ?? []);
	let awardsView = $derived(
		queryView(awardsQuery, {
			policy: 'cached',
			reachable: reachability.current,
			errorMessage: m.quest_tool_history_failed()
		})
	);

	// One dialog for the whole list rather than one per row. The award stays set
	// after closing so the text doesn't blank out during the exit animation.
	let confirmOpen = $state(false);
	let awardToCancel = $state.raw<QuestAwardItemDto | null>(null);
	let pointsToCancel = $derived(m.quest_points({ count: awardToCancel?.amount ?? 0 }));

	const cancelMutation = createMutation(() => ({
		...cancelQuestAwardMutation(),
		// Refetch whichever way it went: a refusal (window expired, cancelled
		// elsewhere) also means this row's button is out of date.
		onSettled: () => queryClient.invalidateQueries({ queryKey: listQuestAwardsQueryKey() })
	}));
	let cancellingId = $derived(
		cancelMutation.isPending ? cancelMutation.variables.path.award_id : undefined
	);

	function askToCancel(award: QuestAwardItemDto) {
		awardToCancel = award;
		confirmOpen = true;
	}

	function handleConfirmCancel() {
		if (!awardToCancel) {
			return;
		}
		cancelMutation.mutate(
			{ path: { award_id: awardToCancel.id } },
			{
				onSuccess: () => toastService.add(m.quest_tool_cancelled(), 'success'),
				onError: (error) =>
					toastService.add(getApiErrorDetail(error) ?? m.quest_tool_cancel_failed(), 'error')
			}
		);
	}

	async function loadMore() {
		const result = await awardsQuery.fetchNextPage();
		if (result.isFetchNextPageError) {
			toastService.add(m.quest_tool_history_failed(), 'error');
		}
	}
</script>

<QueryState view={awardsView}>
	{#snippet loading()}
		<SectionSpinner />
	{/snippet}

	{#snippet ready()}
		{#if awards.length === 0}
			<EmptyState message={m.quest_tool_history_empty()} />
		{:else}
			<Card.Root class="w-full max-w-none gap-0 overflow-hidden rounded-2xl p-0">
				<ul class="divide-y divide-border">
					{#each awards as award (award.id)}
						<QuestAwardItem
							{award}
							{showAwarder}
							cancelling={cancellingId === award.id}
							onCancel={askToCancel}
						/>
					{/each}
				</ul>
			</Card.Root>

			{#if awardsQuery.hasNextPage}
				<LoadMoreButton
					loading={awardsQuery.isFetchingNextPage}
					busy={awardsQuery.isFetching}
					onclick={loadMore}
				/>
			{/if}
		{/if}
	{/snippet}
</QueryState>

<AlertDialog.Root bind:open={confirmOpen}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>{m.quest_tool_cancel_title()}</AlertDialog.Title>
			{#if awardToCancel}
				<AlertDialog.Description>
					{m.quest_tool_cancel_description({
						username: awardToCancel.user.username,
						points: pointsToCancel
					})}
				</AlertDialog.Description>
			{/if}
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<!-- Not the usual «Отмена»: next to «Отменить начисление» it reads as the
			     same action, so the safe button says what it keeps. -->
			<AlertDialog.Cancel>{m.quest_tool_cancel_keep()}</AlertDialog.Cancel>
			<AlertDialog.Action variant="destructive" onclick={handleConfirmCancel}>
				{m.quest_tool_cancel_confirm()}
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
