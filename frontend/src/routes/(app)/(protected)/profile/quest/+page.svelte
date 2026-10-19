<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	import type { GetQuestOutput } from '#lib/api/generated/index.js';
	import type { ReadyView } from '#lib/utils/queryView.js';

	import { getQuestOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import QueryState from '#lib/components/QueryState.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import * as Card from '#lib/components/ui/card/index.js';
	import * as Tabs from '#lib/components/ui/tabs/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { currentUserOptions } from '#lib/services/identity.js';
	import { reachability } from '#lib/services/reachability.js';
	import { queryView } from '#lib/utils/queryView.js';

	import SectionSpinner from '../../../components/SectionSpinner.svelte';
	import LeaderboardRow from './components/LeaderboardRow.svelte';
	import QuestBadge from './components/QuestBadge.svelte';

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

	// Opens on the badge: showing the code is what a player opens the page for.
	let tab = $state('badge');
</script>

<svelte:head>
	<title>{m.document_title({ title: m.quest_title() })}</title>
</svelte:head>

<SectionIntro description={m.quest_intro()} />

<!-- Tabs rather than the map's toggle group: each option here swaps in a
     separate panel, which is the ARIA tabs pattern, while a toggle group only
     reports pressed state. https://www.w3.org/WAI/ARIA/apg/patterns/tabs/ -->
<Tabs.Root bind:value={tab} class="gap-4">
	<Tabs.List aria-label={m.quest_tabs_label()} class="w-full sm:w-auto">
		<Tabs.Trigger value="badge">{m.quest_tab_badge()}</Tabs.Trigger>
		<Tabs.Trigger value="leaderboard">{m.quest_leaderboard_title()}</Tabs.Trigger>
	</Tabs.List>

	<Tabs.Content value="badge">
		{#if user}
			<QuestBadge {user} {quest} />
		{/if}
	</Tabs.Content>

	<Tabs.Content value="leaderboard">
		<QueryState view={questView}>
			{#snippet loading()}
				<SectionSpinner />
			{/snippet}

			{#snippet ready({ data: standings }: ReadyView<GetQuestOutput>)}
				{#if standings.leaderboard.length === 0}
					<EmptyState message={m.quest_leaderboard_empty()} />
				{:else}
					<Card.Root class="w-full max-w-none gap-0 overflow-hidden p-0">
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
	</Tabs.Content>
</Tabs.Root>
