import type { components } from '$lib/api/v1';
import type { CurrentUserDTO, UserPermissionDTO } from '$lib/types/user';

// Permission identifiers, generated from the backend `Permissions` enum via the
// OpenAPI spec (just frontend-generate-api). Typing each constant as
// PermissionName is the drift guard: if the backend renames or removes a
// permission, its literal stops being assignable to this union and `pnpm check`
// fails here — instead of silently shipping a stale string that fails every
// permission check at runtime.
export type PermissionName = components['schemas']['Permissions'];

const SCHEDULE_MANAGE: PermissionName = 'schedule:manage';
const SCHEDULE_IMPORT: PermissionName = 'schedule:import';
const NOTIFICATIONS_SEND: PermissionName = 'notifications:send';
const SETTINGS_MANAGE: PermissionName = 'settings:manage';

/**
 * Check if user has a specific permission.
 * @param user - The user object or null
 * @param permissionName - The permission name to check
 * @returns true if user has the permission, false otherwise
 */
export function hasPermission(
	user: CurrentUserDTO | null,
	permissionName: PermissionName
): boolean {
	if (!user) {
		return false;
	}

	return (
		user.permissions?.some((permission: UserPermissionDTO) => permission.name === permissionName) ??
		false
	);
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
