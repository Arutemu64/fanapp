<script lang="ts">
	import { Search, Card } from 'flowbite-svelte';
	import { ArrowLeftOutline, CheckCircleSolid, UsersGroupOutline } from 'flowbite-svelte-icons';
	import ParticipantCard from '$lib/components/voting/ParticipantCard.svelte';
	import type { VotingParticipantUserDTO, VotingNominationUserDTO } from '$lib/types/voting';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	let nomination: VotingNominationUserDTO = $derived(data.nomination);

	// Local mutable state for participants (allows voting updates)
	let localParticipants: VotingParticipantUserDTO[] = $state([]);
	let participants: VotingParticipantUserDTO[] = $derived(
		localParticipants.length > 0 ? localParticipants : data.participants
	);

	let query = $state('');

	let filtered = $derived(
		participants.filter((p) => {
			const q = query.toLowerCase();
			return p.title.toLowerCase().includes(q) || p.voting_number?.toLowerCase().includes(q);
		})
	);

	let sorted = $derived([...filtered].sort((a, b) => b.votes_count - a.votes_count));

	let hasVoted = $derived(participants.some((p) => p.vote_id !== null));

	function handleVote(participantId: number) {
		localParticipants = participants.map((p) => {
			if (p.id === participantId) {
				return { ...p, vote_id: Date.now(), votes_count: p.votes_count + 1 };
			}
			return p;
		});
	}
</script>

<svelte:head>
	<title>{nomination.title} - Голосование</title>
</svelte:head>

<div class="mb-4 sm:mb-6">
	<a
		href="/voting"
		class="mb-2 inline-flex items-center gap-1 text-xs text-gray-600 hover:text-gray-800 sm:mb-3 sm:text-sm dark:text-gray-400 dark:hover:text-gray-300"
	>
		<ArrowLeftOutline class="h-3 w-3 sm:h-4 sm:w-4" />
		Назад к номинациям
	</a>

	<h1 class="text-lg font-bold text-gray-900 sm:text-xl dark:text-white">{nomination.title}</h1>

	<p class="mt-0.5 text-xs text-gray-500 sm:mt-1 sm:text-sm dark:text-gray-400">
		{#if hasVoted}
			<span class="flex items-center gap-1 text-green-600 dark:text-green-400">
				<CheckCircleSolid class="h-3 w-3 sm:h-4 sm:w-4" />
				Вы уже проголосовали в этой номинации
			</span>
		{:else}
			Выберите участника, чтобы отдать свой голос
		{/if}
	</p>
</div>

<div class="sticky top-0 z-20 mb-3 bg-gray-50 py-2 sm:mb-4 dark:bg-gray-900">
	<Search size="sm" placeholder="Поиск..." clearable bind:value={query} class="w-full" />
</div>

<div class="grid grid-cols-1 gap-2 sm:grid-cols-2 sm:gap-3 lg:grid-cols-3 xl:grid-cols-4">
	{#each sorted as participant (participant.id)}
		<ParticipantCard {participant} onVote={handleVote} />
	{/each}
</div>

{#if sorted.length === 0}
	<Card class="py-8 text-center sm:py-12">
		<UsersGroupOutline class="mx-auto h-10 w-10 text-gray-300 sm:h-12 sm:w-12 dark:text-gray-600" />
		<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">Участники не найдены</p>
	</Card>
{/if}
