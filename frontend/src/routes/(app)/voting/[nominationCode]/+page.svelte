<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { ExternalLink, Search as SearchIcon, Users, X } from '@lucide/svelte';

	import type { GetVotingNominationOutput } from '#lib/api/generated/index.js';

	import EmptyState from '#lib/components/EmptyState.svelte';
	import OfflineUnavailableState from '#lib/components/OfflineUnavailableState.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { createSearchIndex } from '#lib/utils/search.js';

	import type { PageProps } from './$types';

	import ParticipantRow from '../components/ParticipantRow.svelte';
	import UserVoteNotice from '../components/UserVoteNotice.svelte';
	import VotingStatusAlert from '../components/VotingStatusAlert.svelte';

	type VotingParticipant = GetVotingNominationOutput['participants'][number];

	let { data }: PageProps = $props();
	// Absent offline: voting is uncached and online-only (see +page.ts).
	let nomination: GetVotingNominationOutput | undefined = $derived(data.nomination);
	let participants = $derived(nomination?.participants ?? []);
	let votingStatus = $derived(data.votingStatus);
	let canVote = $derived(votingStatus?.can_vote ?? false);

	let searchQuery = $state('');

	let searchIndex = $derived(
		createSearchIndex(participants, (p: VotingParticipant) => [p.title, p.voting_number])
	);

	let filtered = $derived(searchIndex.filter(searchQuery));

	let hasSearchQuery = $derived(searchQuery.trim().length > 0);

	let resultsSummary = $derived(
		filtered.length === participants.length
			? `Всего участников: ${participants.length}`
			: `Показано ${filtered.length} из ${participants.length}`
	);

	let votedParticipant = $derived(
		participants.find((p: VotingParticipant) => p.user_vote !== null)
	);
	let hasVoted = $derived(votedParticipant !== undefined);
	let showVoteHint = $derived(canVote && !hasVoted);

	async function handleVoted() {
		await invalidate('app:voting:nomination');
	}
</script>

<svelte:head>
	<title>{nomination ? `${nomination.title} · ` : ''}Голосование · ФАН ФАН</title>
</svelte:head>

{#if data.offlineUnavailable || !nomination}
	<!-- Voting is uncached and online-only, so there is no saved copy to show —
	     say so plainly instead of crashing on a missing nomination. -->
	<OfflineUnavailableState
		title="Голосование доступно только онлайн"
		message="Подключись к интернету, чтобы голосовать за участников."
	/>
{:else}
	{#if showVoteHint || nomination?.works_url}
		<SectionIntro>
			<!-- Hint on the left, works-preview action on the right. Stacks on narrow
			screens, sits side by side from sm up. -->
			<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				{#if showVoteHint}
					<p class="text-sm text-muted-foreground sm:text-base">
						Выбери участника, чтобы отдать голос
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
						Смотреть работы
					</Button>
				{/if}
			</div>
		</SectionIntro>
	{/if}

	<VotingStatusAlert votingState={votingStatus} class="mb-4" />

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
				aria-label="Поиск участников в номинации"
				placeholder="Поиск по имени или номеру…"
				autocomplete="off"
				spellcheck={false}
				class="pr-8 pl-9"
			/>
			{#if searchQuery}
				<button
					type="button"
					class="absolute right-2 text-muted-foreground hover:text-foreground"
					onclick={() => (searchQuery = '')}
					aria-label="Очистить поиск"
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
		<EmptyState icon={Users} title="Ничего не нашлось" message="Попробуй изменить запрос">
			<button
				onclick={() => (searchQuery = '')}
				class="mt-3 text-sm font-medium text-primary hover:underline"
			>
				Очистить поиск
			</button>
		</EmptyState>
	{:else}
		<EmptyState icon={Users} title="Участников пока нет" message="Появятся ближе к фестивалю" />
	{/if}
{/if}
