<script lang="ts">
	import type { NominationVotingDTO } from '$lib/types/nominations';
	import { Card } from 'flowbite-svelte';
	import { ThumbsUpOutline } from 'flowbite-svelte-icons';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import NominationCard from '$lib/components/voting/NominationCard.svelte';
	import VotingStatusAlert from '$lib/components/voting/VotingStatusAlert.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let nominations: NominationVotingDTO[] = $derived(data.nominations);
	let votingStatus = $derived(data.votingStatus);
</script>

<svelte:head>
	<title>Голосование</title>
</svelte:head>

<SectionHeader title="Голосование" description="Выбери номинацию для голосования" />

<VotingStatusAlert votingState={votingStatus} class="mb-4" />

{#if nominations.length === 0}
	<Card class="py-8 text-center sm:py-12">
		<ThumbsUpOutline class="mx-auto h-10 w-10 text-gray-300 sm:h-12 sm:w-12 dark:text-gray-600" />
		<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">Нет доступных номинаций</p>
	</Card>
{:else}
	<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
		{#each nominations as nomination (nomination.id)}
			<NominationCard {nomination} />
		{/each}
	</div>
{/if}
