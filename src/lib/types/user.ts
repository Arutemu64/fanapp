import type { UserRole } from './role';

export interface UserPermissionDTO {
	name: string;
	object_type: string | null;
	object_id: number | null;
}

export interface FullUserDTO {
	id: number;
	tg_id: number | null;
	username: string | null;
	first_name: string | null;
	last_name: string | null;
	role: UserRole | null;
	permissions: UserPermissionDTO[];
}
