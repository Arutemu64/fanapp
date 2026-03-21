<script lang="ts">
	import { Search, Card, Button } from 'flowbite-svelte';
	import { ArrowLeftOutline, CheckCircleSolid, UsersGroupOutline } from 'flowbite-svelte-icons';
	import ParticipantCard from '$lib/components/voting/ParticipantCard.svelte';
	import VotingStatusAlert from '$lib/components/voting/VotingStatusAlert.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import { invalidate } from '$app/navigation';
	import type { PageProps } from './$types';
	import type { GetVotingNominationResult } from '$lib/types/voting';

	let { data }: PageProps = $props();
	let nominationId = $derived(data.nomination.id);
	let nomination: GetVotingNominationResult = $derived(data.nomination);
	let participants = $derived(nomination.participants);
	let votingStatus = $derived(data.votingStatus);
	let canVote = $derived(votingStatus?.can_vote ?? false);

	let searchQuery = $state('');

	let filtered = $derived(
		participants.filter((p) => {
			const q = searchQuery.toLowerCase();
			return (
				p.title.toLowerCase().includes(q) || p.voting_number?.toString().toLowerCase().includes(q)
			);
		})
	);

	let hasVoted = $derived(participants.some((p) => p.user_vote !== null));

	async function handleVoted() {
		await invalidate('app:voting:nomination');
	}
</script>

<svelte:head>
	<title>{nomination.title} - Голосование</title>
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

<SectionHeader title={nomination.title}>
	<p class="mt-1 text-sm text-gray-500 sm:text-base dark:text-gray-400">
		{#if hasVoted}
			<span class="flex items-center gap-1 text-green-600 dark:text-green-400">
				<CheckCircleSolid class="h-3 w-3 sm:h-4 sm:w-4" />
				Вы уже проголосовали в этой номинации
			</span>
		{:else}
			Выберите участника, чтобы отдать свой голос
		{/if}
	</p>
</SectionHeader>

<VotingStatusAlert votingState={votingStatus} class="mb-4" />

<!-- Search controls -->
<div class="mx-auto mb-4 max-w-2xl">
	<!-- Делаем фильтр таким же спокойным по стилю, как и на странице расписания. -->
	<div
		class="rounded-2xl border border-gray-200 bg-white p-3 shadow-sm dark:border-gray-700 dark:bg-gray-800"
	>
		<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
			<div class="flex-1">
				<Search
					bind:value={searchQuery}
					name="participant_search"
					aria-label="Поиск участников в номинации"
					placeholder="Поиск по имени или номеру…"
					autocomplete="off"
					spellcheck={false}
					clearable
					size="sm"
				/>
			</div>
		</div>
	</div>
</div>

<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3 xl:grid-cols-4">
	{#each filtered as participant (participant.id)}
		<ParticipantCard {participant} {nominationId} {hasVoted} {canVote} onVoted={handleVoted} />
	{:else}
		<div class="col-span-full">
			<Card class="py-8 text-center sm:py-12">
				<UsersGroupOutline
					class="mx-auto h-10 w-10 text-gray-300 sm:h-12 sm:w-12 dark:text-gray-600"
				/>
				<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">Участники не найдены</p>
			</Card>
		</div>
	{/each}
</div>
