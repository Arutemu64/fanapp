<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	import type { SyncSourceStatusDto } from '#lib/api/generated/index.js';
	import type { ReadyView } from '#lib/utils/queryView.js';

	import { getSyncSourcesOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import QueryState from '#lib/components/QueryState.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import * as Tabs from '#lib/components/ui/tabs/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { hasPermission } from '#lib/utils/permissions.js';
	import { queryView } from '#lib/utils/queryView.js';

	import type { PageProps } from './$types';

	import SectionSpinner from '../../../components/SectionSpinner.svelte';
	import SyncSourceCard from '../components/SyncSourceCard.svelte';
	import ToolSection from '../components/ToolSection.svelte';
	import GenerateTicketsForm from './components/GenerateTicketsForm.svelte';
	import TCloudEventRolesForm from './components/TCloudEventRolesForm.svelte';
	import TicketList from './components/TicketList.svelte';

	let { data }: PageProps = $props();

	let canManage = $derived(hasPermission(data.user, 'tickets:manage'));
	let canSync = $derived(hasPermission(data.user, 'sync:run'));
	let canOpenUsers = $derived(hasPermission(data.user, 'users:read'));
	let initialTab = $derived(canManage ? 'list' : 'tcloud');

	const sourcesQuery = createQuery(() => ({ ...getSyncSourcesOptions(), enabled: canSync }));
	let sourcesView = $derived(
		queryView(sourcesQuery, {
			policy: 'cached',
			reachable: reachability.current,
			errorMessage: m.sync_load_failed()
		})
	);
</script>

<svelte:head>
	<title>{m.document_title({ title: m.tool_tickets() })}</title>
</svelte:head>

<div class="mx-auto flex w-full max-w-2xl flex-col gap-4">
	<SectionIntro description={m.tool_tickets_intro()} />

	<Tabs.Root value={initialTab} class="gap-4">
		<Tabs.List aria-label={m.tickets_tabs_label()} class="w-full sm:w-auto">
			{#if canManage}
				<Tabs.Trigger value="list">{m.tickets_tab_list()}</Tabs.Trigger>
				<Tabs.Trigger value="generate">{m.tickets_tab_generate()}</Tabs.Trigger>
			{/if}
			<Tabs.Trigger value="tcloud">{m.tickets_source_tcloud()}</Tabs.Trigger>
		</Tabs.List>

		{#if canManage}
			<Tabs.Content value="list">
				<TicketList {canOpenUsers} />
			</Tabs.Content>

			<Tabs.Content value="generate">
				<ToolSection>
					<GenerateTicketsForm />
				</ToolSection>
			</Tabs.Content>
		{/if}

		<Tabs.Content value="tcloud" class="flex flex-col gap-4">
			{#if canSync}
				<QueryState view={sourcesView}>
					{#snippet loading()}
						<SectionSpinner />
					{/snippet}

					{#snippet ready({ data: sources }: ReadyView<SyncSourceStatusDto[]>)}
						{#each sources.filter((source) => source.source === 'tcloud') as source (source.source)}
							<SyncSourceCard {source} />
						{/each}
					{/snippet}
				</QueryState>
			{/if}

			{#if data.eventRoles}
				<ToolSection title={m.tcloud_roles_title()}>
					{#if !data.eventRoles.available}
						<p class="text-sm text-muted-foreground">{m.sync_not_configured()}</p>
					{/if}
					<TCloudEventRolesForm initial={data.eventRoles} />
				</ToolSection>
			{/if}
		</Tabs.Content>
	</Tabs.Root>
</div>
