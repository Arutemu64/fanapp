<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import { getQuestOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { currentUserOptions } from '#lib/api/index.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import ErrorState from '#lib/components/ErrorState.svelte';
	import OfflineUnavailableState from '#lib/components/OfflineUnavailableState.svelte';
	import QrCode from '#lib/components/QrCode.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import * as Card from '#lib/components/ui/card/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { questCodeFor } from '#lib/utils/questCode.js';

	import SectionSpinner from '../../../components/SectionSpinner.svelte';
	import LeaderboardRow from './components/LeaderboardRow.svelte';

	const userQuery = createQuery(() => currentUserOptions());
	const questQuery = createQuery(() => getQuestOptions());

	let user = $derived(userQuery.data ?? null);
	let quest = $derived(questQuery.data);
	// Offline the query pauses instead of failing, so without this a cold miss
	// would spin forever. The code needs no network and shows regardless.
	let offlineMiss = $derived(quest === undefined && !reachability.current);
	let summary = $derived.by(() => {
		if (!quest) {
			return '';
		}
		// No place until the first points: there is nothing to rank yet.
		if (quest.rank === null) {
			return m.quest_points({ count: 0 });
		}
		return `${m.quest_points({ count: quest.points })} · ${m.quest_rank({ rank: quest.rank })}`;
	});
</script>

<svelte:head>
	<title>{m.document_title({ title: m.quest_title() })}</title>
</svelte:head>

<SectionIntro description={m.quest_intro()} />

{#if user}
	<Card.Root class="w-full max-w-none items-center gap-3 rounded-2xl p-4 text-center sm:p-6">
		<h2 class="text-section text-foreground">{m.quest_code_title()}</h2>
		<!-- Large and edge-to-edge on a phone: the volunteer's camera reads it from
		     arm's length, often in poor hall lighting. -->
		<QrCode
			value={questCodeFor(user.id)}
			label={m.quest_code_label({ username: user.username })}
			class="w-full max-w-64 rounded-lg"
		/>
		{#if summary}
			<p class="text-headline text-foreground">{summary}</p>
		{/if}
		<p class="text-sm text-muted-foreground">{m.quest_code_hint()}</p>
	</Card.Root>
{/if}

<section class="flex flex-col gap-3" aria-labelledby="leaderboard-title">
	<h2 id="leaderboard-title" class="text-section text-foreground">
		{m.quest_leaderboard_title()}
	</h2>

	{#if offlineMiss}
		<OfflineUnavailableState />
	{:else if quest === undefined}
		{#if questQuery.isError}
			<ErrorState
				variant="inline"
				onRetry={() => void questQuery.refetch()}
				error={{
					status: 500,
					message: getApiErrorDetail(questQuery.error) ?? m.quest_load_failed()
				}}
			/>
		{:else}
			<SectionSpinner />
		{/if}
	{:else if quest.leaderboard.length === 0}
		<EmptyState message={m.quest_leaderboard_empty()} />
	{:else}
		<Card.Root class="w-full max-w-none gap-0 overflow-hidden rounded-2xl p-0">
			<ol class="divide-y divide-border">
				{#each quest.leaderboard as entry (entry.player.id)}
					<LeaderboardRow {entry} isOwn={entry.player.id === user?.id} />
				{/each}
			</ol>
			{#if quest.own_entry}
				<!-- The places between the top and the player stay hidden: they only tell
				     someone how far behind they are. The list restarts at their rank. -->
				<p
					class="border-t border-dashed border-border py-1 text-center text-sm text-muted-foreground"
				>
					<span aria-hidden="true">⋯</span>
					<span class="sr-only">{m.quest_leaderboard_gap()}</span>
				</p>
				<ol start={quest.own_entry.rank}>
					<LeaderboardRow entry={quest.own_entry} isOwn />
				</ol>
			{/if}
		</Card.Root>
	{/if}
</section>
