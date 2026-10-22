<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	import { getSyncSourcesOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import * as Tabs from '#lib/components/ui/tabs/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { hasPermission } from '#lib/utils/permissions.js';

	import type { PageProps } from './$types';

	import SyncSourceCard from '../components/SyncSourceCard.svelte';
	import ToolSection from '../components/ToolSection.svelte';
	import GenerateTicketsForm from './components/GenerateTicketsForm.svelte';
	import TCloudEventRolesForm from './components/TCloudEventRolesForm.svelte';
	import TicketList from './components/TicketList.svelte';

	let { data }: PageProps = $props();

	// The tool opens with either permission (see lib/data/tools.ts); each tab
	// shows only what the endpoints behind it would accept.
	let canManage = $derived(hasPermission(data.user, 'tickets:manage'));
	let canSync = $derived(hasPermission(data.user, 'sync:run'));
	let canOpenUsers = $derived(hasPermission(data.user, 'users:read'));
	let initialTab = $derived(canManage ? 'list' : 'tcloud');

	// Kept live by sync_run_updated events (see the root layout).
	const sourcesQuery = createQuery(() => ({ ...getSyncSourcesOptions(), enabled: canSync }));
	let tcloudSource = $derived(
		sourcesQuery.data?.find((source) => source.source === 'tcloud') ?? null
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
			{#if canSync && tcloudSource}
				<SyncSourceCard source={tcloudSource} />
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
