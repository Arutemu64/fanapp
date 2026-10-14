<script lang="ts">
	import type { Path } from '$app/types';
	import type { Component } from 'svelte';

	import {
		Award,
		FileUp,
		Megaphone,
		MessageSquare,
		RotateCw,
		SlidersHorizontal,
		Ticket,
		Users
	} from '@lucide/svelte';

	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import {
		canGenerateTickets,
		canImportSchedule,
		canManageSettings,
		canManageVoting,
		canReadFeedback,
		canReadUsers,
		canRunSync,
		canSendNotifications
	} from '#lib/utils/permissions.js';

	import type { PageProps } from './$types';

	import OnlineNowCard from './components/OnlineNowCard.svelte';
	import ToolRow from './components/ToolRow.svelte';

	let { data }: PageProps = $props();
	// The (protected) guard's snapshot: these rows only gate links.
	let user = $derived(data.user);

	interface Tool {
		key: string;
		title: string;
		description: string;
		icon: Component;
		href: Path;
		/** Whether this org holds the permission this tool needs. */
		canAccess: boolean;
	}

	// Locked tools stay in the list so an org sees the whole toolbox and knows what
	// they'd need granted, rather than the section silently shrinking per account.
	let tools = $derived<Tool[]>([
		{
			key: 'settings',
			title: m.tool_settings_title(),
			description: m.tool_settings_description(),
			icon: SlidersHorizontal,
			href: 'tools/settings',
			canAccess: canManageSettings(user)
		},
		{
			key: 'voting',
			title: m.tool_voting_title(),
			description: m.tool_voting_description(),
			icon: Award,
			href: 'tools/voting',
			canAccess: canManageVoting(user)
		},
		{
			key: 'import-schedule',
			title: m.tool_import_title(),
			description: m.tool_import_description(),
			icon: FileUp,
			href: 'tools/import-schedule',
			canAccess: canImportSchedule(user)
		},
		{
			key: 'broadcast',
			title: m.tool_broadcast_title(),
			description: m.tool_broadcast_description(),
			icon: Megaphone,
			href: 'tools/broadcast',
			canAccess: canSendNotifications(user)
		},
		{
			key: 'generate-tickets',
			title: m.tool_tickets_title(),
			description: m.tool_tickets_description(),
			icon: Ticket,
			href: 'tools/generate-tickets',
			canAccess: canGenerateTickets(user)
		},
		{
			key: 'sync',
			title: m.tool_sync_title(),
			description: m.tool_sync_description(),
			icon: RotateCw,
			href: 'tools/sync',
			canAccess: canRunSync(user)
		},
		{
			key: 'feedback',
			title: m.tool_feedback_title(),
			description: m.tool_feedback_description(),
			icon: MessageSquare,
			href: 'tools/feedback',
			canAccess: canReadFeedback(user)
		},
		{
			key: 'users',
			title: m.tool_users_title(),
			description: m.tool_users_description(),
			icon: Users,
			href: 'tools/users',
			canAccess: canReadUsers(user)
		}
	]);
</script>

<!-- Capped and centred like the /profile hub this menu continues. -->
<div class="mx-auto max-w-2xl">
	<SectionIntro description={m.tools_intro()} />

	<!-- Shown to every org: the tools layout already gates this whole section to the
	     org role, so no per-tool permission scopes the live count. -->
	<div class="mb-4">
		<OnlineNowCard />
	</div>

	<MenuGroup>
		{#each tools as tool (tool.key)}
			<ToolRow
				title={tool.title}
				description={tool.description}
				icon={tool.icon}
				href={tool.href}
				locked={!tool.canAccess}
			/>
		{/each}
	</MenuGroup>
</div>
