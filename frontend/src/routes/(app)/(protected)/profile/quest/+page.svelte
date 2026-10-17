<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';
	import { on } from 'svelte/events';

	import type { GetQuestOutput } from '#lib/api/generated/index.js';
	import type { ReadyView } from '#lib/utils/queryView.js';

	import { getQuestOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import QrCode from '#lib/components/QrCode.svelte';
	import QueryState from '#lib/components/QueryState.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import * as Card from '#lib/components/ui/card/index.js';
	import Username from '#lib/components/Username.svelte';
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

	// A player holds the code up to a volunteer and waits; a dimming screen makes
	// the scan fail. The browser drops the lock whenever the page is hidden, so it
	// is re-requested on return. Refusals (power saving, no support) just leave the
	// screen on its usual timeout.
	// https://developer.mozilla.org/en-US/docs/Web/API/Screen_Wake_Lock_API
	function keepScreenAwake() {
		if (!('wakeLock' in navigator)) {
			return;
		}
		let sentinel: WakeLockSentinel | null = null;
		let released = false;

		async function request() {
			if (document.visibilityState !== 'visible') {
				return;
			}
			try {
				const lock = await navigator.wakeLock.request('screen');
				if (released) {
					void lock.release();
					return;
				}
				sentinel = lock;
			} catch {
				// Refused: nothing to undo.
			}
		}

		void request();
		const stopListening = on(document, 'visibilitychange', () => void request());
		return () => {
			released = true;
			stopListening();
			void sentinel?.release();
		};
	}
</script>

<svelte:head>
	<title>{m.document_title({ title: m.quest_title() })}</title>
</svelte:head>

<SectionIntro description={m.quest_intro()} />

{#if user}
	<!-- First on the page: showing the code is what a player opens it for. -->
	<Card.Root
		class="w-full max-w-none items-center gap-3 p-4 text-center sm:p-6"
		{@attach keepScreenAwake}
	>
		<h2 class="text-section text-foreground">{m.quest_code_title()}</h2>
		<!-- Large and edge-to-edge on a phone: the volunteer's camera reads it from
		     arm's length, often in poor hall lighting. -->
		<QrCode
			value={questCodeFor(user.id)}
			label={m.quest_code_label({ username: user.username })}
			class="w-full max-w-64 rounded-lg"
		/>
		<!-- The fallback when the camera won't read the code: the volunteer's tool
		     can find the player by this name. -->
		<p class="font-sans text-section text-foreground"><Username username={user.username} /></p>
		<p class="text-sm text-muted-foreground">{m.quest_code_hint()}</p>
	</Card.Root>
{/if}

{#if quest}
	<Card.Root class="w-full max-w-none p-4 sm:p-6">
		<dl class="grid auto-cols-fr grid-flow-col gap-4 text-center">
			<div>
				<dt class="text-sm text-muted-foreground">{m.quest_summary_points()}</dt>
				<dd class="font-sans text-headline text-foreground tabular-nums">{quest.points}</dd>
			</div>
			<!-- No place until the first points: there is nothing to rank yet. -->
			{#if quest.rank !== null}
				<div>
					<dt class="text-sm text-muted-foreground">{m.quest_summary_rank()}</dt>
					<dd class="font-sans text-headline text-foreground tabular-nums">{quest.rank}</dd>
				</div>
			{/if}
		</dl>
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
</section>
