<script lang="ts">
	import ThumbsUp from '@lucide/svelte/icons/thumbs-up';
	import { createQuery } from '@tanstack/svelte-query';

	import type { ListVotingNominationsOutput } from '#lib/api/generated/index.js';
	import type { ReadyView } from '#lib/utils/queryView.js';

	import {
		getVotingStatusOptions,
		listVotingNominationsOptions
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import QueryState from '#lib/components/QueryState.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { queryView } from '#lib/utils/queryView.js';

	import NominationCard from './components/NominationCard.svelte';
	import VotingSkeleton from './components/VotingSkeleton.svelte';
	import VotingStatusAlert from './components/VotingStatusAlert.svelte';

	const nominationsQuery = createQuery(() => listVotingNominationsOptions());
	const votingStatusQuery = createQuery(() => getVotingStatusOptions());

	// Voting is a live, online-only surface: casting a vote is a mutation, and the
	// open/closed and already-voted state must not be shown stale (a ballot you
	// can't submit is a dead end). So it is never persisted, and a copy still in
	// memory from earlier in the session is not shown offline either.
	let nominationsView = $derived(
		queryView(nominationsQuery, {
			policy: 'live',
			reachable: reachability.current,
			errorMessage: m.voting_nominations_load_failed()
		})
	);
</script>

<svelte:head>
	<title>{m.document_title({ title: m.nav_voting() })}</title>
</svelte:head>

<QueryState view={nominationsView}>
	{#snippet loading()}
		<VotingSkeleton />
	{/snippet}

	{#snippet ready({ data }: ReadyView<ListVotingNominationsOutput>)}
		<VotingStatusAlert votingState={votingStatusQuery.data} class="mb-4" />

		{#if data.nominations.length === 0}
			<EmptyState icon={ThumbsUp} message={m.voting_nominations_empty()} />
		{:else}
			<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
				{#each data.nominations as nomination (nomination.id)}
					<NominationCard {nomination} />
				{/each}
			</div>
		{/if}
	{/snippet}
</QueryState>
