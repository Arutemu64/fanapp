<script lang="ts">
	import type { NominationVotingDto } from '$lib/api/generated';

	import { votingNominationsQueryOptions, votingStatusQueryOptions } from '$lib/api/queries';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import OfflineUnavailableState from '$lib/components/OfflineUnavailableState.svelte';
	import { ThumbsUp } from '@lucide/svelte';
	import { createQuery } from '@tanstack/svelte-query';

	import NominationCard from './components/NominationCard.svelte';
	import VotingStatusAlert from './components/VotingStatusAlert.svelte';

	const nominationsQuery = createQuery(votingNominationsQueryOptions);
	// Same key as the voting layout's own read, so the two share one request.
	const statusQuery = createQuery(votingStatusQueryOptions);

	let nominations: NominationVotingDto[] = $derived(nominationsQuery.data ?? []);
	let votingStatus = $derived(statusQuery.data);

	// Voting is uncached and online-only (networkMode 'online'), so offline the
	// query parks as `paused` with nothing to show rather than failing.
	let offlineUnavailable = $derived(nominationsQuery.isPaused || nominationsQuery.isError);
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
	<VotingStatusAlert votingState={votingStatus} class="mb-4" />

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
