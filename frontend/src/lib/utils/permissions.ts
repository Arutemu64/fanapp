import type { CurrentUserDto, Permission } from '#lib/api/generated/index.js';

import { m } from '#lib/paraglide/messages.js';

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

export function canManagePermissions(user: CurrentUserDto | null): boolean {
	return hasPermission(user, WILDCARD);
}

export const PERMISSION_LABELS: Record<Permission, () => string> = {
	'*': m.permission_all,
	'schedule:manage': m.permission_schedule_manage,
	'schedule:setup': m.permission_schedule_setup,
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
