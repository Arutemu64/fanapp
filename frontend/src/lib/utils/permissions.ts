import type { CurrentUserDTO, UserPermissionDTO } from '$lib/types/user';

/**
 * Check if user has a specific permission.
 * @param user - The user object or null
 * @param permissionName - The permission name to check (e.g., 'schedule:manage')
 * @returns true if user has the permission, false otherwise
 */
export function hasPermission(user: CurrentUserDTO | null, permissionName: string): boolean {
	if (!user) {
		return false;
	}

	// ORG is the staff admin role and implicitly holds every permission,
	// mirroring the bypass in the backend's PermissionService.ensure.
	if (user.role === 'org') {
		return true;
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
