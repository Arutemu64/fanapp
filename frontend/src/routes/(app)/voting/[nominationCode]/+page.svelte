<script lang="ts">
	import { page } from '$app/state';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Users from '@lucide/svelte/icons/users';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';

	import type { GetVotingNominationOutput } from '#lib/api/generated/index.js';

	import {
		getVotingNominationOptions,
		getVotingNominationQueryKey,
		getVotingStatusOptions,
		listVotingNominationsQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import QueryState from '#lib/components/QueryState.svelte';
	import SearchInput from '#lib/components/SearchInput.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Skeleton } from '#lib/components/ui/skeleton/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { queryView } from '#lib/utils/queryView.js';
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

	let nominationView = $derived(
		queryView(nominationQuery, {
			policy: 'live',
			reachable: reachability.current,
			errorMessage: m.voting_nomination_load_failed()
		})
	);
	let nomination: GetVotingNominationOutput | undefined = $derived(
		nominationView.kind === 'ready' ? nominationView.data : undefined
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

<QueryState view={nominationView}>
	{#snippet loading()}
		<div role="status" aria-live="polite" class="flex flex-col gap-3">
			<span class="sr-only">{m.voting_participants_loading()}</span>
			<Skeleton class="h-10 w-full rounded-lg" />
			<Skeleton class="h-64 w-full rounded-xl" />
		</div>
	{/snippet}

	{#snippet ready()}
		{#if showVoteHint || nomination?.works_url}
			<SectionIntro>
				<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
					{#if showVoteHint}
						<p class="text-body text-muted-foreground">
							{m.voting_pick_participant()}
						</p>
					{/if}
					{#if nomination?.works_url}
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

		<div class="mb-4 flex flex-col gap-2">
			<SearchInput
				bind:value={searchQuery}
				name="participant_search"
				label={m.voting_participants_search_label()}
				placeholder={m.voting_participants_search_placeholder()}
			/>

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
			<EmptyState
				icon={Users}
				title={m.common_nothing_found()}
				message={m.voting_try_other_query()}
			>
				<button
					type="button"
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
	{/snippet}
</QueryState>
