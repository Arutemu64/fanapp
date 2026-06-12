import { WILDCARD_PERMISSION } from '$lib/constants/permissions';
import type { CurrentUserDTO, UserPermissionDTO } from '$lib/types/user';

/**
 * Check if user has a specific permission.
 * @param user - The user object or null
 * @param permissionName - The permission name to check (e.g., 'can_manage_schedule')
 * @param objectType - Optional object type for object-specific permissions
 * @param objectId - Optional object ID for object-specific permissions
 * @returns true if user has the permission, false otherwise
 */
export function hasPermission(
	user: CurrentUserDTO | null,
	permissionName: string,
	objectType?: string,
	objectId?: number
): boolean {
	if (!user || !user.permissions) {
		return false;
	}

	return user.permissions.some((permission: UserPermissionDTO) => {
		// The backend ships a wildcard for roles that implicitly hold every
		// permission (e.g. ORG), so it satisfies any check regardless of object.
		if (permission.name === WILDCARD_PERMISSION) {
			return true;
		}

		if (permission.name !== permissionName) {
			return false;
		}

		// If no object type/id specified, just check permission name
		if (objectType === undefined && objectId === undefined) {
			return true;
		}

		// Check object type if specified
		if (objectType !== undefined && permission.object_type !== objectType) {
			return false;
		}

		// Check object id if specified
		if (objectId !== undefined && permission.object_id !== objectId) {
			return false;
		}

		return true;
	});
}

/**
 * Check if user can manage schedule
 * @param user - The user object or null
 * @returns true if user has 'can_manage_schedule' permission
 */
export function canManageSchedule(user: CurrentUserDTO | null): boolean {
	return hasPermission(user, 'schedule:manage');
}
