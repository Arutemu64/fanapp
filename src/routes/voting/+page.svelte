<script lang="ts">
	import { Card, Progressbar } from 'flowbite-svelte';
	import { CheckCircleSolid } from 'flowbite-svelte-icons';
	import NominationCard from '$lib/components/voting/NominationCard.svelte';
	import type { VotingNominationUserDTO } from '$lib/types/voting';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	let nominations: VotingNominationUserDTO[] = $derived(data.nominations);

	let votedCount = $derived(nominations.filter((n) => n.vote_id !== null).length);
	let totalCount = $derived(nominations.length);
	let progressPercent = $derived(totalCount > 0 ? Math.round((votedCount / totalCount) * 100) : 0);
</script>

<svelte:head>
	<title>Голосование</title>
</svelte:head>

<div class="mb-4 sm:mb-6">
	<h1 class="text-lg font-bold text-gray-900 sm:text-xl dark:text-white">Голосование</h1>
	<p class="mt-0.5 text-xs text-gray-500 sm:mt-1 sm:text-sm dark:text-gray-400">
		Выберите номинацию для голосования
	</p>

	<div class="mt-2 sm:mt-3">
		<div class="mb-1 flex items-center justify-between">
			<span class="text-xs text-gray-500 sm:text-sm dark:text-gray-400">Прогресс голосования</span>
			<span class="text-xs font-medium text-gray-700 sm:text-sm dark:text-gray-300">
				{votedCount}/{totalCount}
			</span>
		</div>
		<Progressbar progress={progressPercent} color="green" size="h-2" />
	</div>

	{#if votedCount === totalCount && totalCount > 0}
		<div
			class="mt-1.5 flex items-center gap-1 text-xs text-green-600 sm:mt-2 sm:text-sm dark:text-green-400"
		>
			<CheckCircleSolid class="h-3.5 w-3.5 sm:h-4 sm:w-4" />
			Вы проголосовали во всех номинациях!
		</div>
	{/if}
</div>

<div class="grid grid-cols-1 gap-2 sm:grid-cols-2 sm:gap-3 lg:grid-cols-3 xl:grid-cols-4">
	{#each nominations as nomination (nomination.id)}
		<NominationCard {nomination} />
	{/each}
</div>

{#if nominations.length === 0}
	<Card class="py-8 text-center sm:py-12">
		<p class="text-sm text-gray-500 dark:text-gray-400">Номинации не найдены</p>
	</Card>
{/if}
