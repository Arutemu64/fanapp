import type { CurrentUserDto, Permission } from '#lib/api/generated/index.js';

import { m } from '#lib/paraglide/messages.js';

// Permission identifiers, from the backend `Permission` enum via the OpenAPI
// spec (just frontend-generate-api). Typing each literal as Permission is the
// drift guard: if the backend renames or removes a permission, its literal stops
// being assignable to this union and `pnpm check` fails here — instead of
// silently shipping a stale string that fails every permission check at runtime.

// Superuser grant: a holder passes every permission check. Kept in sync with the
// backend Permission enum through the generated union above.
const WILDCARD: Permission = '*';

export function hasPermission(user: CurrentUserDto | null, permission: Permission): boolean {
	if (!user) {
		return false;
	}

	const granted = user.permissions;
	return granted.includes(WILDCARD) || granted.includes(permission);
}

export function isOrganizer(user: CurrentUserDto | null): boolean {
	return user?.role === 'organizer';
}

// The toolbox is a staff surface: volunteers and organizers reach it. Access to
// each tool inside stays permission-based, so this gate governs visibility of the
// section, never the actions.
export function isStaff(user: CurrentUserDto | null): boolean {
	return user?.role === 'organizer' || user?.role === 'volunteer';
}

export function canManageSchedule(user: CurrentUserDto | null): boolean {
	return hasPermission(user, 'schedule:manage');
}

export function canManageUsers(user: CurrentUserDto | null): boolean {
	return hasPermission(user, 'users:manage');
}

export function canAwardQuest(user: CurrentUserDto | null): boolean {
	return hasPermission(user, 'quest:award');
}

export function canManageQuest(user: CurrentUserDto | null): boolean {
	return hasPermission(user, 'quest:manage');
}

// Handing out permissions takes the superuser grant itself: whoever may grant
// them can give any of them to a second account of their own.
export function canManagePermissions(user: CurrentUserDto | null): boolean {
	return hasPermission(user, WILDCARD);
}

// A Record over the generated union, so a permission the backend adds fails
// `pnpm check` here until it has a label. Insertion order is display order.
export const PERMISSION_LABELS: Record<Permission, () => string> = {
	'*': m.permission_all,
	'schedule:manage': m.permission_schedule_manage,
	'schedule:import': m.tool_import_schedule,
	'notifications:send': m.tool_broadcast,
	'settings:manage': m.tool_settings,
	'tickets:manage': m.tool_tickets,
	'sync:run': m.tool_sync,
	'demo:seed': m.permission_demo_seed,
	'feedback:read': m.permission_feedback_read,
	'voting:manage': m.permission_voting_manage,
	'users:read': m.permission_users_read,
	'users:manage': m.permission_users_manage,
	'quest:award': m.permission_quest_award,
	'quest:manage': m.permission_quest_manage
};
