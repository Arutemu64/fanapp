<script lang="ts">
	import { createInfiniteQuery } from '@tanstack/svelte-query';

	import { questHistoryFeedOptions } from '#lib/api/offlineQueries.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import QueryState from '#lib/components/QueryState.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { formatRelativeTime } from '#lib/utils/formatters.js';
	import { queryView } from '#lib/utils/queryView.js';

	import SectionSpinner from '../../../../components/SectionSpinner.svelte';

	const historyQuery = createInfiniteQuery(() => questHistoryFeedOptions());

	let awards = $derived(historyQuery.data?.pages.flatMap((page) => page.awards) ?? []);
	let historyView = $derived(
		queryView(historyQuery, {
			policy: 'cached',
			reachable: reachability.current,
			errorMessage: m.quest_history_failed()
		})
	);

	let listElement = $state<HTMLElement | null>(null);
</script>

<QueryState view={historyView}>
	{#snippet loading()}
		<SectionSpinner />
	{/snippet}

	{#snippet offline()}
		<EmptyState title={m.quest_history_offline_title()} message={m.quest_offline_message()} />
	{/snippet}

	{#snippet ready()}
		{#if awards.length === 0}
			<EmptyState message={m.quest_history_empty()} />
		{:else}
			<Card.Root class="w-full max-w-none gap-0 overflow-hidden p-0">
				<ul class="divide-y divide-border" bind:this={listElement}>
					{#each awards as award (award.id)}
						{const cancelled = $derived(award.cancelled_at !== null)}
						<li class="flex items-start gap-3 p-3 sm:px-4">
							<div class="min-w-0 flex-1">
								<p class="text-sm wrap-break-word text-foreground">{award.message}</p>
								<p class="text-xs text-muted-foreground">{formatRelativeTime(award.created_at)}</p>
							</div>
							<!-- Struck through rather than dropped: the player was told about both
							     the award and its cancellation, so the list keeps both. -->
							<div class="flex shrink-0 flex-col items-end gap-1">
								<span
									class={[
										'text-base font-semibold text-foreground tabular-nums',
										cancelled && 'text-muted-foreground line-through'
									]}
								>
									+{m.quest_points({ count: award.amount })}
								</span>
								{#if cancelled}
									<Badge variant="secondary">{m.quest_history_cancelled()}</Badge>
								{/if}
							</div>
						</li>
					{/each}
				</ul>
			</Card.Root>

			<LoadMoreButton
				query={historyQuery}
				list={listElement}
				errorMessage={m.quest_history_failed()}
			/>
		{/if}
	{/snippet}
</QueryState>
