<script lang="ts">
	import type { NominationVotingDTO } from '$lib/types/nominations';

	import EmptyState from '$lib/components/EmptyState.svelte';
	import { ThumbsUpOutline } from 'flowbite-svelte-icons';

	import type { PageProps } from './$types';

	import NominationCard from './components/NominationCard.svelte';
	import VotingStatusAlert from './components/VotingStatusAlert.svelte';

	let { data }: PageProps = $props();
	let nominations: NominationVotingDTO[] = $derived(data.nominations);
	let votingStatus = $derived(data.votingStatus);
</script>

<svelte:head>
	<title>Голосование · ФАН ФАН</title>
</svelte:head>

<VotingStatusAlert votingState={votingStatus} class="mb-4" />

{#if nominations.length === 0}
	<EmptyState icon={ThumbsUpOutline} message="Нет доступных номинаций" />
{:else}
	<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
		{#each nominations as nomination (nomination.id)}
			<NominationCard {nomination} />
		{/each}
	</div>
{/if}
