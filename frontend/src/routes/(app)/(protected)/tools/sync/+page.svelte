<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	import type { SyncSourceStatusDto } from '#lib/api/generated/index.js';
	import type { ReadyView } from '#lib/utils/queryView.js';

	import { getSyncSourcesOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import QueryState from '#lib/components/QueryState.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { queryView } from '#lib/utils/queryView.js';

	import SectionSpinner from '../../../components/SectionSpinner.svelte';
	import SyncSourceCard from '../components/SyncSourceCard.svelte';

	// Kept live by sync_run_updated events (see the root layout).
	const sourcesQuery = createQuery(() => getSyncSourcesOptions());
	let sourcesView = $derived(
		queryView(sourcesQuery, {
			policy: 'cached',
			reachable: reachability.current,
			errorMessage: m.sync_load_failed()
		})
	);
</script>

<svelte:head>
	<title>{m.document_title({ title: m.tool_sync() })}</title>
</svelte:head>

<SectionIntro description={m.sync_description()} />

<QueryState view={sourcesView}>
	{#snippet loading()}
		<SectionSpinner />
	{/snippet}

	{#snippet ready({ data: sources }: ReadyView<SyncSourceStatusDto[]>)}
		<div class="mx-auto flex w-full max-w-2xl flex-col gap-4">
			<!-- TicketsCloud syncs from the tickets tool, next to the event roles it applies. -->
			{#each sources.filter((source) => source.source !== 'tcloud') as source (source.source)}
				<SyncSourceCard {source} />
			{/each}
		</div>
	{/snippet}
</QueryState>
