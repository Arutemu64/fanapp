<script lang="ts">
	import type { GetVotingNominationOutput } from '$lib/api/generated';

	import { page } from '$app/state';
	import {
		getVotingNominationOptions,
		getVotingStatusOptions
	} from '$lib/api/generated/@tanstack/svelte-query.gen';
	import BackLink from '$lib/components/BackLink.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { getOfflineService } from '$lib/services/offline.svelte';
	import { createSearchIndex } from '$lib/utils/search';
	import {
		AlertCircle,
		CheckCircle2,
		ExternalLink,
		Search as SearchIcon,
		Users,
		X
	} from '@lucide/svelte';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';

	import ParticipantCard from '../components/ParticipantCard.svelte';
	import VotingStatusAlert from '../components/VotingStatusAlert.svelte';

	type VotingParticipant = GetVotingNominationOutput['participants'][number];

	const queryClient = useQueryClient();
	const offline = getOfflineService();

	let nominationCode = $derived(page.params.nominationCode ?? '');

	// `gcTime: 0` keeps the ballot out of the persisted cache (see +page.ts), so
	// offline there is nothing to show — the honest answer for a mutation surface.
	let nominationOptions = $derived(
		getVotingNominationOptions({ path: { nomination_code: nominationCode } })
	);
	const nominationQuery = createQuery(() => ({ ...nominationOptions, gcTime: 0 }));
	const statusQuery = createQuery(() => getVotingStatusOptions());

	let nomination: GetVotingNominationOutput | undefined = $derived(nominationQuery.data);
	let participants = $derived(nomination?.participants ?? []);
	let canVote = $derived(statusQuery.data?.can_vote ?? false);
	let offlineUnavailable = $derived(!offline.isOnline || (nominationQuery.isError && !nomination));

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
		await queryClient.invalidateQueries({ queryKey: nominationOptions.queryKey });
	}
</script>

<svelte:head>
	<title>{nomination ? `${nomination.title} · ` : ''}Голосование · ФАН ФАН</title>
</svelte:head>

<BackLink href="/voting" label="Назад к номинациям" />

{#if offlineUnavailable || !nomination}
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

	<VotingStatusAlert votingState={statusQuery.data} class="mb-4" />

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
