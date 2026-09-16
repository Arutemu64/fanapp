import type { CurrentUserDto, Permission } from '$lib/api/generated';

// Permission identifiers, from the backend `Permission` enum via the OpenAPI
// spec (just frontend-generate-api). Typing each constant as Permission is the
// drift guard: if the backend renames or removes a permission, its literal stops
// being assignable to this union and `pnpm check` fails here — instead of
// silently shipping a stale string that fails every permission check at runtime.

// Superuser grant: a holder passes every permission check. Kept in sync with the
// backend Permission enum through the generated union above.
const WILDCARD: Permission = '*';

const SCHEDULE_MANAGE: Permission = 'schedule:manage';
const SCHEDULE_IMPORT: Permission = 'schedule:import';
const NOTIFICATIONS_SEND: Permission = 'notifications:send';
const SETTINGS_MANAGE: Permission = 'settings:manage';
const TICKETS_GENERATE: Permission = 'tickets:generate';
const SYNC_RUN: Permission = 'sync:run';
const FEEDBACK_READ: Permission = 'feedback:read';
const VOTING_MANAGE: Permission = 'voting:manage';
const USERS_READ: Permission = 'users:read';

export function hasPermission(user: CurrentUserDto | null, permission: Permission): boolean {
	if (!user) {
		return false;
	}

	const granted = user.permissions;
	if (!granted) {
		return false;
	}

	return granted.includes(WILDCARD) || granted.includes(permission);
}

// The staff toolbox is an organiser surface: only the org role reaches it at all.
// Access to each individual tool inside stays permission-based (an org may hold
// any subset), so this gate governs visibility of the section, never the actions.
export function isOrg(user: CurrentUserDto | null): boolean {
	return user?.role === 'org';
}

export function canManageSchedule(user: CurrentUserDto | null): boolean {
	return hasPermission(user, SCHEDULE_MANAGE);
}

export function canImportSchedule(user: CurrentUserDto | null): boolean {
	return hasPermission(user, SCHEDULE_IMPORT);
}

export function canSendNotifications(user: CurrentUserDto | null): boolean {
	return hasPermission(user, NOTIFICATIONS_SEND);
}

export function canManageSettings(user: CurrentUserDto | null): boolean {
	return hasPermission(user, SETTINGS_MANAGE);
}

export function canGenerateTickets(user: CurrentUserDto | null): boolean {
	return hasPermission(user, TICKETS_GENERATE);
}

export function canRunSync(user: CurrentUserDto | null): boolean {
	return hasPermission(user, SYNC_RUN);
}

export function canReadFeedback(user: CurrentUserDto | null): boolean {
	return hasPermission(user, FEEDBACK_READ);
}

export function canManageVoting(user: CurrentUserDto | null): boolean {
	return hasPermission(user, VOTING_MANAGE);
}

export function canReadUsers(user: CurrentUserDto | null): boolean {
	return hasPermission(user, USERS_READ);
}
