<script lang="ts">
	import type { GetVotingNominationResult } from '$lib/types/voting';

	import { invalidate } from '$app/navigation';
	import BackLink from '$lib/components/BackLink.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { createSearchIndex } from '$lib/utils/search';
	import {
		AlertCircle,
		CheckCircle2,
		ExternalLink,
		Search as SearchIcon,
		Users,
		X
	} from '@lucide/svelte';

	import type { PageProps } from './$types';

	import ParticipantCard from '../components/ParticipantCard.svelte';
	import VotingStatusAlert from '../components/VotingStatusAlert.svelte';

	type VotingParticipant = GetVotingNominationResult['participants'][number];

	let { data }: PageProps = $props();
	// Absent offline: voting is uncached and online-only (see +page.ts).
	let nomination: GetVotingNominationResult | undefined = $derived(data.nomination);
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

	let hasVoted = $derived(participants.some((p: VotingParticipant) => p.user_vote !== null));

	async function handleVoted() {
		await invalidate('app:voting:nomination');
	}
</script>

<svelte:head>
	<title>{nomination ? `${nomination.title} · ` : ''}Голосование · ФАН ФАН</title>
</svelte:head>

<BackLink href="/voting" label="Назад к номинациям" />

{#if data.offlineUnavailable || !nomination}
	<!-- Voting is uncached and online-only, so there is no saved copy to show —
	     say so plainly instead of crashing on a missing nomination. -->
	<EmptyState
		icon={AlertCircle}
		title="Голосование доступно только онлайн"
		message="Подключись к интернету, чтобы голосовать за участников."
	/>
{:else}
	<SectionIntro>
		<!-- Title/description on the left, works-preview action on the right.
		Stacks on narrow screens, sits side by side from sm up. -->
		<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
			<div>
				<!-- Navbar shows the generic "Голосование"; the nomination name is the page's
				own heading (h2) so long names stay readable instead of clipping in the navbar. -->
				<h2 class="text-xl font-bold text-foreground">{nomination?.title}</h2>
				<p class="mt-1 text-sm text-muted-foreground sm:text-base">
					{#if hasVoted}
						<span class="flex items-center gap-1 text-success">
							<CheckCircle2 class="size-4" />
							Голос в этой номинации учтён
						</span>
					{:else if canVote}
						Выбери участника, чтобы отдать голос
					{/if}
				</p>
			</div>
			{#if nomination?.works_url}
				<!-- External gallery of the nominated works; opens in a new tab. -->
				<Button
					href={nomination.works_url}
					rel="external noopener"
					target="_blank"
					size="sm"
					class="shrink-0"
				>
					<ExternalLink data-icon="inline-start" />
					Смотреть работы
				</Button>
			{/if}
		</div>
	</SectionIntro>

	<VotingStatusAlert votingState={votingStatus} class="mb-4" />

	<div class="relative mb-2 flex items-center">
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
     feedback that the grid shrank or grew. Matches the schedule page. Skipped
     for an empty nomination: there is nothing to filter, and the empty state
     below already says so. -->
	{#if participants.length > 0}
		<p class="mb-4 text-xs text-muted-foreground" aria-live="polite" role="status">
			{resultsSummary}
		</p>
	{/if}

	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
		{#each filtered as participant (participant.id)}
			<ParticipantCard {participant} {hasVoted} {canVote} onVoted={handleVoted} />
		{:else}
			<div class="col-span-full">
				<!-- Two distinct states: a search that matched nothing (recoverable —
			     offer the reset), and a nomination with no participants at all,
			     where clearing the search would do nothing. -->
				{#if hasSearchQuery}
					<EmptyState icon={Users} title="Ничего не нашлось" message="Попробуй изменить запрос">
						<button
							onclick={() => (searchQuery = '')}
							class="mt-3 text-sm font-medium text-primary hover:underline"
						>
							Очистить поиск
						</button>
					</EmptyState>
				{:else}
					<EmptyState
						icon={Users}
						title="Участников пока нет"
						message="Появятся ближе к фестивалю"
					/>
				{/if}
			</div>
		{/each}
	</div>
{/if}
