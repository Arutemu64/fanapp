<script lang="ts">
	import { page } from '$app/state';
	import { ExternalLink, Search as SearchIcon, Users, X } from '@lucide/svelte';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';

	import type { GetVotingNominationOutput } from '#lib/api/generated/index.js';

	import { getApiErrorDetail, isConnectionFailure } from '#lib/api/errors.js';
	import {
		getVotingNominationOptions,
		getVotingNominationQueryKey,
		getVotingStatusOptions,
		listVotingNominationsQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import ErrorState from '#lib/components/ErrorState.svelte';
	import OfflineUnavailableState from '#lib/components/OfflineUnavailableState.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Skeleton } from '#lib/components/ui/skeleton/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { createSearchIndex } from '#lib/utils/search.js';

	import ParticipantRow from '../components/ParticipantRow.svelte';
	import UserVoteNotice from '../components/UserVoteNotice.svelte';
	import VotingStatusAlert from '../components/VotingStatusAlert.svelte';

	type VotingParticipant = GetVotingNominationOutput['participants'][number];

	const queryClient = useQueryClient();
	let nominationCode = $derived(page.params.nominationCode ?? '');
	const nominationQuery = createQuery(() =>
		getVotingNominationOptions({ path: { nomination_code: nominationCode } })
	);
	const votingStatusQuery = createQuery(() => getVotingStatusOptions());

	// Never shown from the cache offline: voting is a live, online-only surface
	// (see ../+page.svelte). A read that got no answer counts as offline too, as
	// on the nominations list, rather than holding the skeleton until the probe
	// confirms it or the retries run out.
	let offline = $derived(
		!reachability.current ||
			(nominationQuery.data === undefined && isConnectionFailure(nominationQuery.failureReason))
	);
	let nomination: GetVotingNominationOutput | undefined = $derived(
		offline ? undefined : nominationQuery.data
	);
	let participants = $derived(nomination?.participants ?? []);
	let canVote = $derived(votingStatusQuery.data?.can_vote ?? false);

	let searchQuery = $state('');

	let searchIndex = $derived(
		createSearchIndex(participants, (p: VotingParticipant) => [p.title, p.voting_number])
	);

	let filtered = $derived(searchIndex.filter(searchQuery));

	let hasSearchQuery = $derived(searchQuery.trim().length > 0);

	let resultsSummary = $derived(
		filtered.length === participants.length
			? m.voting_total_participants({ count: participants.length })
			: m.results_shown_of({ count: filtered.length, total: participants.length })
	);

	let votedParticipant = $derived(
		participants.find((p: VotingParticipant) => p.user_vote !== null)
	);
	let hasVoted = $derived(votedParticipant !== undefined);
	let showVoteHint = $derived(canVote && !hasVoted);

	async function handleVoted() {
		void queryClient.invalidateQueries({ queryKey: listVotingNominationsQueryKey() });
		await queryClient.invalidateQueries({
			queryKey: getVotingNominationQueryKey({ path: { nomination_code: nominationCode } })
		});
	}
</script>

<svelte:head>
	<title>
		{m.document_title({
			title: nomination ? `${nomination.title} · ${m.nav_voting()}` : m.nav_voting()
		})}
	</title>
</svelte:head>

{#if offline}
	<!-- Voting is online-only, so there is no saved copy to show — say so plainly
	     instead of crashing on a missing nomination. -->
	<OfflineUnavailableState title={m.voting_offline_title()} message={m.voting_offline_message()} />
{:else if !nomination}
	<!-- Online with nothing to show: the load gave up waiting (it leaves a
	     connection failure to the page) or the request failed. Blaming the
	     connection here would be wrong, so this says what actually happened. -->
	{#if nominationQuery.isError}
		<ErrorState
			variant="inline"
			onRetry={() => void nominationQuery.refetch()}
			error={{
				status: 500,
				message: getApiErrorDetail(nominationQuery.error) ?? m.voting_nomination_load_failed()
			}}
		/>
	{:else}
		<div role="status" aria-live="polite" class="flex flex-col gap-3">
			<span class="sr-only">{m.voting_participants_loading()}</span>
			<Skeleton class="h-10 w-full rounded-lg" />
			<Skeleton class="h-64 w-full rounded-xl" />
		</div>
	{/if}
{:else}
	{#if showVoteHint || nomination?.works_url}
		<SectionIntro>
			<!-- Hint on the left, works-preview action on the right. Stacks on narrow
			screens, sits side by side from sm up. -->
			<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				{#if showVoteHint}
					<p class="text-sm text-muted-foreground sm:text-base">
						{m.voting_pick_participant()}
					</p>
				{/if}
				{#if nomination?.works_url}
					<!-- External gallery of the nominated works; opens in a new tab. -->
					<Button
						href={nomination.works_url}
						rel="external noopener"
						target="_blank"
						size="sm"
						class="shrink-0 self-start"
					>
						<ExternalLink data-icon="inline-start" />
						{m.voting_see_works()}
					</Button>
				{/if}
			</div>
		</SectionIntro>
	{/if}

	<VotingStatusAlert votingState={votingStatusQuery.data} class="mb-4" />

	<!-- Above the search on purpose: the voted participant can be filtered out of
	     the list, and this is where the vote is taken back. -->
	{#if votedParticipant?.user_vote}
		<div class="mb-4">
			<UserVoteNotice
				participant={votedParticipant}
				vote={votedParticipant.user_vote}
				{canVote}
				onCancelled={handleVoted}
			/>
		</div>
	{/if}

	<!-- Search sits straight on the page, as on the schedule, so the two lists read
	     alike (DESIGN "When not to" use a card). -->
	<div class="mb-4 flex flex-col gap-2">
		<div class="relative flex items-center">
			<SearchIcon class="pointer-events-none absolute left-3 size-4 text-muted-foreground" />
			<Input
				bind:value={searchQuery}
				name="participant_search"
				aria-label={m.voting_participants_search_label()}
				placeholder={m.voting_participants_search_placeholder()}
				autocomplete="off"
				spellcheck={false}
				class="pr-8 pl-9"
			/>
			{#if searchQuery}
				<button
					type="button"
					class="absolute right-2 text-muted-foreground hover:text-foreground"
					onclick={() => (searchQuery = '')}
					aria-label={m.common_clear_search()}
				>
					<X class="size-4" />
				</button>
			{/if}
		</div>

		<!-- Announce filter result changes to screen readers, which otherwise get no
		     feedback that the list shrank or grew. Shown only while searching, as on the
		     schedule: an unfiltered total tells a sighted user nothing. Skipped for an
		     empty nomination: there is nothing to filter, and the empty state below
		     already says so. -->
		{#if participants.length > 0}
			<p
				class={['px-1 text-xs text-muted-foreground', !hasSearchQuery && 'sr-only']}
				aria-live="polite"
				role="status"
			>
				{resultsSummary}
			</p>
		{/if}
	</div>

	{#if filtered.length > 0}
		<div class="overflow-clip rounded-xl border border-border bg-card">
			<ul class="divide-y divide-border">
				{#each filtered as participant (participant.id)}
					<ParticipantRow {participant} {hasVoted} {canVote} onVoted={handleVoted} />
				{/each}
			</ul>
		</div>
	{:else if hasSearchQuery}
		<!-- Two distinct states: a search that matched nothing (recoverable —
		     offer the reset), and a nomination with no participants at all,
		     where clearing the search would do nothing. -->
		<EmptyState icon={Users} title={m.common_nothing_found()} message={m.voting_try_other_query()}>
			<button
				onclick={() => (searchQuery = '')}
				class="mt-3 text-sm font-medium text-primary hover:underline"
			>
				{m.common_clear_search()}
			</button>
		</EmptyState>
	{:else}
		<EmptyState
			icon={Users}
			title={m.voting_participants_empty_title()}
			message={m.voting_participants_empty_message()}
		/>
	{/if}
{/if}
