import type { CurrentUserDTO, UserPermissionDTO } from '$lib/types/user';

import { WILDCARD_PERMISSION } from '$lib/constants/permissions';

/**
 * Check if user has a specific permission.
 * @param user - The user object or null
 * @param permissionName - The permission name to check (e.g., 'schedule:manage')
 * @returns true if user has the permission, false otherwise
 */
export function hasPermission(user: CurrentUserDTO | null, permissionName: string): boolean {
	if (!user || !user.permissions) {
		return false;
	}

	return user.permissions.some((permission: UserPermissionDTO) => {
		// The backend ships a wildcard for roles that implicitly hold every
		// permission (e.g. ORG), so it satisfies any check.
		if (permission.name === WILDCARD_PERMISSION) {
			return true;
		}

		return permission.name === permissionName;
	});
}

/**
 * Check if user can manage schedule
 * @param user - The user object or null
 * @returns true if user has 'schedule:manage' permission
 */
export function canManageSchedule(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, 'schedule:manage');
}

/**
 * Check if user can import a schedule file.
 * @param user - The user object or null
 * @returns true if user has 'schedule:import' permission
 */
export function canImportSchedule(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, 'schedule:import');
}

/**
 * Check if user can send notification broadcasts.
 * @param user - The user object or null
 * @returns true if user has 'notifications:send' permission
 */
export function canSendNotifications(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, 'notifications:send');
}

/**
 * Check if user can manage festival settings.
 * @param user - The user object or null
 * @returns true if user has 'settings:manage' permission
 */
export function canManageSettings(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, 'settings:manage');
}
