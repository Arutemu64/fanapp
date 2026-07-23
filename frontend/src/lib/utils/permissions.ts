import type { components } from '$lib/api/v1';
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

/**
 * Check if user has a specific permission.
 * @param user - The user object or null
 * @param permission - The permission to check
 * @returns true if user has the permission, false otherwise
 */
export function hasPermission(user: CurrentUserDTO | null, permission: Permission): boolean {
	if (!user) {
		return false;
	}

	return user.permissions?.includes(permission) ?? false;
}

/**
 * Check if user can manage schedule
 * @param user - The user object or null
 * @returns true if user has 'schedule:manage' permission
 */
export function canManageSchedule(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, SCHEDULE_MANAGE);
}

/**
 * Check if user can import a schedule file.
 * @param user - The user object or null
 * @returns true if user has 'schedule:import' permission
 */
export function canImportSchedule(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, SCHEDULE_IMPORT);
}

/**
 * Check if user can send notification broadcasts.
 * @param user - The user object or null
 * @returns true if user has 'notifications:send' permission
 */
export function canSendNotifications(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, NOTIFICATIONS_SEND);
}

/**
 * Check if user can manage festival settings.
 * @param user - The user object or null
 * @returns true if user has 'settings:manage' permission
 */
export function canManageSettings(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, SETTINGS_MANAGE);
}

/**
 * Check if user can generate tickets.
 * @param user - The user object or null
 * @returns true if user has 'tickets:generate' permission
 */
export function canGenerateTickets(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, TICKETS_GENERATE);
}

/**
 * Check if user can run external syncs (Cosplay2 / TicketsCloud).
 * @param user - The user object or null
 * @returns true if user has 'sync:run' permission
 */
export function canRunSyncs(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, SYNC_RUN);
}
