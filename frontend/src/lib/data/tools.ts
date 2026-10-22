import type { Path } from '$app/types';
import type { Component } from 'svelte';

import Award from '@lucide/svelte/icons/award';
import Coins from '@lucide/svelte/icons/coins';
import FileUp from '@lucide/svelte/icons/file-up';
import Megaphone from '@lucide/svelte/icons/megaphone';
import MessageSquare from '@lucide/svelte/icons/message-square';
import RotateCw from '@lucide/svelte/icons/rotate-cw';
import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';
import Ticket from '@lucide/svelte/icons/ticket';
import Users from '@lucide/svelte/icons/users';
import { error } from '@sveltejs/kit';

import type { CurrentUserDto, Permission, PublicConfigDto } from '#lib/api/generated/index.js';

import { m } from '#lib/paraglide/messages.js';
import { hasPermission } from '#lib/utils/permissions.js';

export type ToolKey =
	| 'broadcast'
	| 'feedback'
	| 'import-schedule'
	| 'quest'
	| 'settings'
	| 'sync'
	| 'tickets'
	| 'users'
	| 'voting';

interface Tool {
	key: ToolKey;
	title: () => string;
	description: () => string;
	icon: Component;
	href: Path;
	/** Holding any one of these opens the tool. Typed as `Permission` so a backend rename fails `pnpm check`. */
	anyOf: Permission[];
	/** The tool is also off while the festival quest is. */
	requiresQuest?: boolean;
	/** Opens offline: its writes wait in the queue (ADR-0038). Every other tool is online-only. */
	worksOffline?: boolean;
	/** Copy for the 403 a direct visit gets. */
	forbidden: () => string;
}

export type ToolConfig = Pick<PublicConfigDto, 'quest_enabled'>;

// Display order of the dashboard. Mirrors the backend permission each tool's
// endpoints enforce, so a page is never shown to someone its requests would reject.
const TOOLS: Tool[] = [
	{
		key: 'settings',
		title: m.tool_settings,
		description: m.tool_settings_description,
		icon: SlidersHorizontal,
		href: 'tools/settings',
		anyOf: ['settings:manage'],
		forbidden: m.settings_forbidden
	},
	{
		key: 'voting',
		title: m.nav_voting,
		description: m.tool_voting_description,
		icon: Award,
		href: 'tools/voting',
		anyOf: ['voting:manage'],
		forbidden: m.voting_admin_forbidden
	},
	{
		key: 'import-schedule',
		title: m.tool_import_schedule,
		description: m.tool_import_schedule_description,
		icon: FileUp,
		href: 'tools/import-schedule',
		anyOf: ['schedule:import'],
		forbidden: m.import_forbidden
	},
	{
		key: 'broadcast',
		title: m.tool_broadcast,
		description: m.tool_broadcast_description,
		icon: Megaphone,
		href: 'tools/broadcast',
		anyOf: ['notifications:send'],
		forbidden: m.broadcast_forbidden
	},
	{
		// tickets:generate lists, issues and maps tickets; sync:run alone still
		// opens it for the TicketsCloud sync, which lives here.
		key: 'tickets',
		title: m.tool_tickets,
		description: m.tool_tickets_description,
		icon: Ticket,
		href: 'tools/tickets',
		anyOf: ['tickets:generate', 'sync:run'],
		forbidden: m.tickets_forbidden
	},
	{
		key: 'sync',
		title: m.tool_sync,
		description: m.tool_sync_description,
		icon: RotateCw,
		href: 'tools/sync',
		anyOf: ['sync:run'],
		forbidden: m.sync_forbidden
	},
	{
		key: 'feedback',
		title: m.tool_feedback,
		description: m.tool_feedback_description,
		icon: MessageSquare,
		href: 'tools/feedback',
		anyOf: ['feedback:read'],
		forbidden: m.tool_feedback_forbidden
	},
	{
		key: 'users',
		title: m.tool_users,
		description: m.tool_users_description,
		icon: Users,
		href: 'tools/users',
		anyOf: ['users:read'],
		forbidden: m.users_forbidden
	},
	{
		// quest:award gives points; quest:manage reviews and cancels every award.
		key: 'quest',
		title: m.tool_quest,
		description: m.tool_quest_description,
		icon: Coins,
		href: 'tools/quest',
		anyOf: ['quest:award', 'quest:manage'],
		requiresQuest: true,
		worksOffline: true,
		forbidden: m.tool_quest_forbidden
	}
];

function holds(tool: Tool, user: CurrentUserDto | null, config: ToolConfig): boolean {
	if (tool.requiresQuest && !config.quest_enabled) {
		return false;
	}
	return tool.anyOf.some((permission) => hasPermission(user, permission));
}

/** The tools this user may open, in dashboard order. */
export function toolsFor(user: CurrentUserDto | null, config: ToolConfig) {
	return TOOLS.filter((tool) => holds(tool, user, config)).map((tool) => ({
		key: tool.key,
		title: tool.title(),
		description: tool.description(),
		icon: tool.icon,
		href: tool.href,
		worksOffline: tool.worksOffline === true
	}));
}

/** The tool pages that open offline, for the toolbox's offline redirect. */
export const OFFLINE_TOOL_HREFS: Path[] = TOOLS.filter((tool) => tool.worksOffline).map(
	(tool) => tool.href
);

/** Page guard: throws the tool's own 403 unless this user may open it. */
export function requireTool(key: ToolKey, user: CurrentUserDto | null, config: ToolConfig): void {
	const tool = TOOLS.find((candidate) => candidate.key === key);
	if (!tool || !holds(tool, user, config)) {
		error(403, tool?.forbidden() ?? m.tools_forbidden());
	}
}
