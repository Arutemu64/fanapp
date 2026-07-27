<script lang="ts">
	import type { GetVotingNominationResult } from '$lib/types/voting';

	import { invalidate } from '$app/navigation';
	import { page } from '$app/state';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { createSearchIndex } from '$lib/utils/search';
	import { createUrlFilterSync } from '$lib/utils/urlFilters';
	import { Button, Search } from 'flowbite-svelte';
	import {
		ArrowLeftOutline,
		ArrowUpRightFromSquareOutline,
		CheckCircleSolid,
		UsersGroupOutline
	} from 'flowbite-svelte-icons';

	import type { PageProps } from './$types';

	import ParticipantCard from '../components/ParticipantCard.svelte';
	import VotingStatusAlert from '../components/VotingStatusAlert.svelte';

	type VotingParticipant = GetVotingNominationResult['participants'][number];

	let { data }: PageProps = $props();
	let nomination: GetVotingNominationResult = $derived(data.nomination);
	let participants = $derived(nomination.participants);
	let votingStatus = $derived(data.votingStatus);
	let canVote = $derived(votingStatus?.can_vote ?? false);

	const SEARCH_PARAM = 'q';

	// Seeded from the query string once, then owned here — same reasoning as the
	// schedule page: a `load` that read the param would re-run on every keystroke.
	// The param rides this nomination's URL, so each nomination keeps its own.
	let searchQuery = $state(page.url.searchParams.get(SEARCH_PARAM) ?? '');

	const urlFilters = createUrlFilterSync();

	function syncSearchUrl(options?: { debounce?: boolean }) {
		urlFilters.set({ [SEARCH_PARAM]: searchQuery.trim() }, options);
	}

	function clearSearch() {
		searchQuery = '';
		syncSearchUrl();
	}

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
	<title>{nomination.title} · Голосование · ФАН ФАН</title>
</svelte:head>

<Button
	href="/voting"
	outline
	size="sm"
	color="alternative"
	class="mb-2 sm:mb-3"
	aria-label="Назад к номинациям"
>
	<ArrowLeftOutline class="mr-1 h-4 w-4" />
	Назад к номинациям
</Button>

<SectionIntro>
	<!-- Title/description on the left, works-preview action on the right.
		Stacks on narrow screens, sits side by side from sm up. -->
	<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
		<div>
			<!-- Navbar shows the generic "Голосование"; the nomination name is the page's
				own heading (h2) so long names stay readable instead of clipping in the navbar. -->
			<h2 class="text-xl font-bold text-gray-900 dark:text-white">{nomination.title}</h2>
			<p class="mt-1 text-sm text-gray-500 sm:text-base dark:text-gray-400">
				{#if hasVoted}
					<span class="flex items-center gap-1 text-green-600 dark:text-green-400">
						<CheckCircleSolid class="h-3 w-3 sm:h-4 sm:w-4" />
						Голос в этой номинации учтён
					</span>
				{:else if canVote}
					Выбери участника, чтобы отдать голос
				{/if}
			</p>
		</div>
		{#if nomination.works_url}
			<!-- External gallery of the nominated works; opens in a new tab. -->
			<Button
				href={nomination.works_url}
				rel="external noopener"
				target="_blank"
				size="sm"
				color="primary"
				class="shrink-0"
			>
				<ArrowUpRightFromSquareOutline class="mr-1 h-4 w-4" />
				Смотреть работы
			</Button>
		{/if}
	</div>
</SectionIntro>

<VotingStatusAlert votingState={votingStatus} class="mb-4" />

<!-- Function binding rather than `bind:value` plus a handler: the setter is the one
     place both typing and the clearable "×" pass through. Flowbite clears by writing
     `undefined`, hence the fallback. -->
<Search
	bind:value={
		() => searchQuery,
		(value: string | undefined) => {
			searchQuery = value ?? '';
			syncSearchUrl({ debounce: true });
		}
	}
	name="participant_search"
	aria-label="Поиск участников в номинации"
	placeholder="Поиск по имени или номеру…"
	autocomplete="off"
	spellcheck={false}
	clearable
	size="sm"
	class="mb-2"
/>

<!-- Announce filter result changes to screen readers, which otherwise get no
     feedback that the grid shrank or grew. Matches the schedule page. Skipped
     for an empty nomination: there is nothing to filter, and the empty state
     below already says so. -->
{#if participants.length > 0}
	<p class="mb-4 text-xs text-gray-500 dark:text-gray-400" aria-live="polite" role="status">
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
				<EmptyState
					icon={UsersGroupOutline}
					title="Ничего не нашлось"
					message="Попробуй изменить запрос"
				>
					<button
						onclick={clearSearch}
						class="mt-3 text-sm font-medium text-primary-600 hover:underline dark:text-primary-400"
					>
						Очистить поиск
					</button>
				</EmptyState>
			{:else}
				<EmptyState
					icon={UsersGroupOutline}
					title="Участников пока нет"
					message="Появятся ближе к фестивалю"
				/>
			{/if}
		</div>
	{/each}
</div>
