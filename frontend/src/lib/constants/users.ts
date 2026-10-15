import type { UserRole } from '#lib/api/generated/index.js';

// Rows per page in the organizer user directory, loaded with "Показать ещё".
export const USERS_PAGE_SIZE = 20;

// Display order of the roles in the directory filter and the role picker.
export const USER_ROLES: UserRole[] = ['visitor', 'participant', 'volunteer', 'organizer'];
