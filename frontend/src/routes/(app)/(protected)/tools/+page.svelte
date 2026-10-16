<script lang="ts">
	import type { Path } from '$app/types';
	import type { Component } from 'svelte';

	import {
		Award,
		Coins,
		FileUp,
		Megaphone,
		MessageSquare,
		RotateCw,
		SlidersHorizontal,
		Ticket,
		Users
	} from '@lucide/svelte';
	import { createQuery } from '@tanstack/svelte-query';

	import { getPublicConfigOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { FALLBACK_CONFIG } from '#lib/constants/festival.js';
	import { m } from '#lib/paraglide/messages.js';
	import {
		canAwardQuest,
		canGenerateTickets,
		canImportSchedule,
		canManageQuest,
		canManageSettings,
		canManageVoting,
		canReadFeedback,
		canReadUsers,
		canRunSync,
		canSendNotifications,
		isOrganizer
	} from '#lib/utils/permissions.js';

	import type { PageProps } from './$types';

	import OnlineNowCard from './components/OnlineNowCard.svelte';
	import ToolRow from './components/ToolRow.svelte';

	let { data }: PageProps = $props();
	// The (protected) guard's snapshot: these rows only gate links.
	let user = $derived(data.user);
	let organizer = $derived(isOrganizer(user));

	const configQuery = createQuery(() => getPublicConfigOptions());
	let questEnabled = $derived((configQuery.data ?? FALLBACK_CONFIG).quest_enabled);

	interface Tool {
		key: string;
		title: string;
		description: string;
		icon: Component;
		href: Path;
		/** Whether this organizer holds the permission this tool needs. */
		canAccess: boolean;
	}

	// Locked tools stay in an organizer's list so they see the whole toolbox and know
	// what they'd need granted. A volunteer sees only what they hold: the organizer
	// tools are not theirs to ask for.
	let allTools = $derived<Tool[]>([
		{
			key: 'settings',
			title: m.tool_settings(),
			description: m.tool_settings_description(),
			icon: SlidersHorizontal,
			href: 'tools/settings',
			canAccess: canManageSettings(user)
		},
		{
			key: 'voting',
			title: m.nav_voting(),
			description: m.tool_voting_description(),
			icon: Award,
			href: 'tools/voting',
			canAccess: canManageVoting(user)
		},
		{
			key: 'import-schedule',
			title: m.tool_import_schedule(),
			description: m.tool_import_schedule_description(),
			icon: FileUp,
			href: 'tools/import-schedule',
			canAccess: canImportSchedule(user)
		},
		{
			key: 'broadcast',
			title: m.tool_broadcast(),
			description: m.tool_broadcast_description(),
			icon: Megaphone,
			href: 'tools/broadcast',
			canAccess: canSendNotifications(user)
		},
		{
			key: 'generate-tickets',
			title: m.tool_generate_tickets(),
			description: m.tool_generate_tickets_description(),
			icon: Ticket,
			href: 'tools/generate-tickets',
			canAccess: canGenerateTickets(user)
		},
		{
			key: 'sync',
			title: m.tool_sync(),
			description: m.tool_sync_description(),
			icon: RotateCw,
			href: 'tools/sync',
			canAccess: canRunSync(user)
		},
		{
			key: 'feedback',
			title: m.tool_feedback(),
			description: m.tool_feedback_description(),
			icon: MessageSquare,
			href: 'tools/feedback',
			canAccess: canReadFeedback(user)
		},
		{
			key: 'users',
			title: m.tool_users(),
			description: m.tool_users_description(),
			icon: Users,
			href: 'tools/users',
			canAccess: canReadUsers(user)
		},
		{
			key: 'quest',
			title: m.tool_quest(),
			description: m.tool_quest_description(),
			icon: Coins,
			href: 'tools/quest',
			canAccess: canAwardQuest(user) || canManageQuest(user)
		}
	]);

	// The quest tool hides with the quest itself, like the profile card.
	let tools = $derived(
		allTools.filter((tool) => {
			if (tool.key === 'quest' && !questEnabled) {
				return false;
			}
			return organizer || tool.canAccess;
		})
	);
</script>

<!-- Capped and centred like the /profile hub this menu continues. -->
<div class="mx-auto max-w-2xl">
	{#if organizer}
		<SectionIntro description={m.tools_intro()} />
	{:else}
		<!-- A volunteer's list holds only their own tools, so the organizer intro's
		     note about locked tools does not apply. -->
		<SectionIntro description={m.tools_intro_volunteer()} />
	{/if}

	<!-- Shown to every organizer, with no per-tool permission scoping the live count;
	     volunteers come here for their own tools only. -->
	{#if organizer}
		<div class="mb-4">
			<OnlineNowCard />
		</div>
	{/if}

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
