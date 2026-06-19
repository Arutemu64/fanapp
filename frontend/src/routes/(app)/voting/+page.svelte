<script lang="ts">
	import type { NominationVotingDTO } from '$lib/types/nominations';
	import { Card } from 'flowbite-svelte';
	import { ThumbsUpOutline } from 'flowbite-svelte-icons';
	import NominationCard from './components/NominationCard.svelte';
	import VotingStatusAlert from './components/VotingStatusAlert.svelte';
	import StaleDataNotice from '$lib/components/StaleDataNotice.svelte';
	import { getOfflineService } from '$lib/services/offline.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let nominations: NominationVotingDTO[] = $derived(data.nominations);
	let votingStatus = $derived(data.votingStatus);

	// Show the notice when the loaded copy is cached (data.stale) or the device went
	// offline since open — what's on screen may be out of date until reconnect.
	const offline = getOfflineService();
	let showStaleNotice = $derived(data.stale || !offline.isOnline);
</script>

<svelte:head>
	<title>Голосование · ФАН ФАН</title>
</svelte:head>

{#if showStaleNotice}
	<StaleDataNotice
		message="Нет связи. Показаны сохранённые номинации — обновятся при подключении."
	/>
{/if}

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
