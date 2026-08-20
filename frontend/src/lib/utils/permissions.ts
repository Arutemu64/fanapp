import type { components } from '$lib/api/schema';
import type { CurrentUserDTO } from '$lib/types/user';

// Permission identifiers, generated from the backend `Permission` enum via the
// OpenAPI spec (just frontend-generate-api). Typing each constant as Permission
// is the drift guard: if the backend renames or removes a permission, its
// literal stops being assignable to this union and `pnpm check` fails here —
// instead of silently shipping a stale string that fails every permission check
// at runtime.
export type Permission = components['schemas']['Permission'];

const SCHEDULE_MANAGE: Permission = 'schedule:manage';
const SCHEDULE_IMPORT: Permission = 'schedule:import';
const NOTIFICATIONS_SEND: Permission = 'notifications:send';
const SETTINGS_MANAGE: Permission = 'settings:manage';
const TICKETS_GENERATE: Permission = 'tickets:generate';
const SYNC_RUN: Permission = 'sync:run';
const FEEDBACK_READ: Permission = 'feedback:read';

export function hasPermission(user: CurrentUserDTO | null, permission: Permission): boolean {
	if (!user) {
		return false;
	}

	return user.permissions?.includes(permission) ?? false;
}

// The staff toolbox is an organiser surface: only the org role reaches it at all.
// Access to each individual tool inside stays permission-based (an org may hold
// any subset), so this gate governs visibility of the section, never the actions.
export function isOrg(user: CurrentUserDTO | null): boolean {
	return user?.role === 'org';
}

export function canManageSchedule(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, SCHEDULE_MANAGE);
}

export function canImportSchedule(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, SCHEDULE_IMPORT);
}

export function canSendNotifications(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, NOTIFICATIONS_SEND);
}

export function canManageSettings(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, SETTINGS_MANAGE);
}

export function canGenerateTickets(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, TICKETS_GENERATE);
}

export function canRunSync(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, SYNC_RUN);
}

export function canReadFeedback(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, FEEDBACK_READ);
}
