<script lang="ts">
	import { Search, Card } from 'flowbite-svelte';
	import { ArrowLeftOutline, CheckCircleSolid, UsersGroupOutline } from 'flowbite-svelte-icons';
	import ParticipantCard from '$lib/components/voting/ParticipantCard.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import { invalidateAll } from '$app/navigation';
	import type { PageProps } from './$types';
	import type { GetVotingNominationResult } from '$lib/types/voting';

	let { data }: PageProps = $props();
	let nominationId = $derived(data.nomination.id);
	let nomination: GetVotingNominationResult = $derived(data.nomination);
	let participants = $derived(nomination.participants);

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
		await invalidateAll();
	}
</script>

<svelte:head>
	<title>{nomination.title} - Голосование</title>
</svelte:head>

<a
	href="/voting"
	class="mb-2 inline-flex items-center gap-1 text-xs text-gray-600 hover:text-gray-800 sm:mb-3 sm:text-sm dark:text-gray-400 dark:hover:text-gray-300"
>
	<ArrowLeftOutline class="h-3 w-3 sm:h-4 sm:w-4" />
	Назад к номинациям
</a>

<SectionHeader title={nomination.title}>
	{#snippet children()}
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
	{/snippet}
</SectionHeader>

<!-- Floating Control Center -->
<div class="sticky top-4 z-40 mx-auto mb-4 max-w-2xl">
	<div
		class="rounded-xl border border-gray-200 bg-white p-3 shadow-lg dark:border-gray-700 dark:bg-gray-800"
	>
		<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
			<div class="flex-1">
				<Search bind:value={searchQuery} placeholder="Поиск..." clearable size="sm" />
			</div>
		</div>
	</div>
</div>

<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3 xl:grid-cols-4">
	{#each filtered as participant (participant.id)}
		<ParticipantCard {participant} {nominationId} {hasVoted} onVoted={handleVoted} />
	{/each}
</div>

{#if filtered.length === 0}
	<Card class="py-8 text-center sm:py-12">
		<UsersGroupOutline class="mx-auto h-10 w-10 text-gray-300 sm:h-12 sm:w-12 dark:text-gray-600" />
		<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">Участники не найдены</p>
	</Card>
{/if}
