<script lang="ts">
	import type { NominationVotingDto } from '$lib/api/generated';

	import {
		getVotingStatusOptions,
		listVotingNominationsOptions
	} from '$lib/api/generated/@tanstack/svelte-query.gen';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import OfflineUnavailableState from '$lib/components/OfflineUnavailableState.svelte';
	import { getOfflineService } from '$lib/services/offline.svelte';
	import { ThumbsUp } from '@lucide/svelte';
	import { createQuery } from '@tanstack/svelte-query';

	import NominationCard from './components/NominationCard.svelte';
	import VotingStatusAlert from './components/VotingStatusAlert.svelte';

	const offline = getOfflineService();

	// `gcTime: 0` keeps the ballot out of the persisted cache (see +page.ts), so
	// offline there is nothing to show — which is the honest answer for a surface
	// whose whole point is a mutation.
	const nominationsQuery = createQuery(() => ({ ...listVotingNominationsOptions(), gcTime: 0 }));
	const statusQuery = createQuery(() => getVotingStatusOptions());

	let nominations: NominationVotingDto[] = $derived(nominationsQuery.data?.nominations ?? []);
	let offlineUnavailable = $derived(
		!offline.isOnline || (nominationsQuery.isError && nominations.length === 0)
	);
</script>

<svelte:head>
	<title>Голосование · ФАН ФАН</title>
</svelte:head>

{#if offlineUnavailable}
	<!-- Voting is uncached and online-only, so there is no saved copy to show —
	     say so plainly instead of an empty "no nominations" state. -->
	<OfflineUnavailableState
		title="Голосование доступно только онлайн"
		message="Подключись к интернету, чтобы голосовать за участников."
	/>
{:else}
	<VotingStatusAlert votingState={statusQuery.data} class="mb-4" />

	{#if nominations.length === 0}
		<EmptyState icon={ThumbsUp} message="Номинаций пока нет" />
	{:else}
		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
			{#each nominations as nomination (nomination.id)}
				<NominationCard {nomination} />
			{/each}
		</div>
	{/if}
{/if}
