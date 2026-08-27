<script lang="ts">
	import type { NominationVotingDTO } from '$lib/types/nominations';

	import EmptyState from '$lib/components/EmptyState.svelte';
	import OfflineUnavailableState from '$lib/components/OfflineUnavailableState.svelte';
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

{#if data.offlineUnavailable}
	<!-- Voting is uncached and online-only, so there is no saved copy to show —
	     say so plainly instead of an empty "no nominations" state. -->
	<OfflineUnavailableState
		title="Голосование доступно только онлайн"
		message="Подключись к интернету, чтобы голосовать за участников."
	/>
{:else}
	<VotingStatusAlert votingState={votingStatus} class="mb-4" />

	{#if nominations.length === 0}
		<EmptyState icon={ThumbsUpOutline} message="Номинаций пока нет" />
	{:else}
		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
			{#each nominations as nomination (nomination.id)}
				<NominationCard {nomination} />
			{/each}
		</div>
	{/if}
{/if}
