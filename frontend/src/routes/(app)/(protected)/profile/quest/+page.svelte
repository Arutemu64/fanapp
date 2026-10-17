<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	import type { GetQuestOutput } from '#lib/api/generated/index.js';
	import type { ReadyView } from '#lib/utils/queryView.js';

	import { getQuestOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import QrCode from '#lib/components/QrCode.svelte';
	import QueryState from '#lib/components/QueryState.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import * as Card from '#lib/components/ui/card/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { currentUserOptions } from '#lib/services/identity.js';
	import { reachability } from '#lib/services/reachability.js';
	import { queryView } from '#lib/utils/queryView.js';
	import { questCodeFor } from '#lib/utils/questCode.js';

	import SectionSpinner from '../../../components/SectionSpinner.svelte';
	import LeaderboardRow from './components/LeaderboardRow.svelte';

	const userQuery = createQuery(() => currentUserOptions());
	// Other players' awards send this viewer no signal, so an open page polls to keep
	// the standings current. One query per viewer every 30s is cheap (the ranking
	// is a ~12 ms aggregate at festival scale), and a broadcast on every award would
	// make every open client refetch at once instead. TanStack skips the tick while
	// the app is in the background.
	const LEADERBOARD_REFRESH_MS = 30_000;
	const questQuery = createQuery(() => ({
		...getQuestOptions(),
		refetchInterval: LEADERBOARD_REFRESH_MS,
		meta: { quietRefetchErrors: true }
	}));

	let user = $derived(userQuery.data ?? null);
	let quest = $derived(questQuery.data);
	// The code needs no network and shows regardless; only the standings wait on
	// the server.
	let questView = $derived(
		queryView(questQuery, {
			policy: 'cached',
			reachable: reachability.current,
			errorMessage: m.quest_load_failed()
		})
	);
	let summary = $derived.by(() => {
		if (!quest) {
			return '';
		}
		// No place until the first points: there is nothing to rank yet.
		if (quest.rank === null) {
			return m.quest_points({ count: quest.points });
		}
		return `${m.quest_points({ count: quest.points })} · ${m.quest_rank({ rank: quest.rank })}`;
	});
</script>

<svelte:head>
	<title>{m.document_title({ title: m.quest_title() })}</title>
</svelte:head>

<SectionIntro description={m.quest_intro()} />

{#if summary}
	<Card.Root class="w-full max-w-none items-center rounded-2xl p-4 text-center sm:p-6">
		<p class="text-headline text-foreground">{summary}</p>
	</Card.Root>
{/if}

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
		<p class="text-sm text-muted-foreground">{m.quest_code_hint()}</p>
	</Card.Root>
{/if}

<section class="flex flex-col gap-3" aria-labelledby="leaderboard-title">
	<h2 id="leaderboard-title" class="text-section text-foreground">
		{m.quest_leaderboard_title()}
	</h2>

	<QueryState view={questView}>
		{#snippet loading()}
			<SectionSpinner />
		{/snippet}

		{#snippet ready({ data: standings }: ReadyView<GetQuestOutput>)}
			{#if standings.leaderboard.length === 0}
				<EmptyState message={m.quest_leaderboard_empty()} />
			{:else}
				<Card.Root class="w-full max-w-none gap-0 overflow-hidden rounded-2xl p-0">
					<ol class="divide-y divide-border">
						{#each standings.leaderboard as entry (entry.player.id)}
							<LeaderboardRow {entry} isOwn={entry.player.id === user?.id} />
						{/each}
					</ol>
					{#if standings.own_entry}
						<!-- The places between the top and the player stay hidden: they only tell
				     someone how far behind they are. The list restarts at their rank. -->
						<p
							class="border-t border-dashed border-border py-1 text-center text-sm text-muted-foreground"
						>
							<span aria-hidden="true">⋯</span>
							<span class="sr-only">{m.quest_leaderboard_gap()}</span>
						</p>
						<ol start={standings.own_entry.rank}>
							<LeaderboardRow entry={standings.own_entry} isOwn />
						</ol>
					{/if}
				</Card.Root>
			{/if}
		{/snippet}
	</QueryState>
</section>
