<script lang="ts">
	import { ThumbsUp } from '@lucide/svelte';
	import { createQuery } from '@tanstack/svelte-query';

	import { getApiErrorDetail, isConnectionFailure } from '#lib/api/errors.js';
	import {
		getVotingStatusOptions,
		listVotingNominationsOptions
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import ErrorState from '#lib/components/ErrorState.svelte';
	import OfflineUnavailableState from '#lib/components/OfflineUnavailableState.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';

	import NominationCard from './components/NominationCard.svelte';
	import VotingSkeleton from './components/VotingSkeleton.svelte';
	import VotingStatusAlert from './components/VotingStatusAlert.svelte';

	const nominationsQuery = createQuery(() => listVotingNominationsOptions());
	const votingStatusQuery = createQuery(() => getVotingStatusOptions());

	let nominations = $derived(nominationsQuery.data?.nominations ?? []);
	// A read that got no answer means the same here as being offline, without
	// waiting for the reachability probe to confirm it or for the retries to run
	// out: `failureReason` is set on the first failed attempt.
	let offline = $derived(
		!reachability.current ||
			(nominationsQuery.data === undefined && isConnectionFailure(nominationsQuery.failureReason))
	);
</script>

<svelte:head>
	<title>{m.document_title({ title: m.nav_voting() })}</title>
</svelte:head>

{#if offline}
	<!-- Voting is a live, online-only surface: casting a vote is a mutation, and the
	     open/closed and already-voted state must not be shown stale (a ballot you
	     can't submit is a dead end). So it is never persisted, and a copy still in
	     memory from earlier in the session is not shown offline either. -->
	<OfflineUnavailableState />
{:else if nominationsQuery.data === undefined}
	{#if nominationsQuery.isError}
		<ErrorState
			variant="inline"
			onRetry={() => void nominationsQuery.refetch()}
			error={{
				status: 500,
				message: getApiErrorDetail(nominationsQuery.error) ?? m.voting_nominations_load_failed()
			}}
		/>
	{:else}
		<VotingSkeleton />
	{/if}
{:else}
	<VotingStatusAlert votingState={votingStatusQuery.data} class="mb-4" />

	{#if nominations.length === 0}
		<EmptyState icon={ThumbsUp} message={m.voting_nominations_empty()} />
	{:else}
		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
			{#each nominations as nomination (nomination.id)}
				<NominationCard {nomination} />
			{/each}
		</div>
	{/if}
{/if}
