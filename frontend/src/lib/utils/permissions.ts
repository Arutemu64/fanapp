import type { CurrentUserDto, Permission } from '#lib/api/generated/index.js';

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
const USERS_MANAGE: Permission = 'users:manage';

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

// The staff toolbox is an organizer surface: only the organizer role reaches it at all.
// Access to each individual tool inside stays permission-based (an organizer may hold
// any subset), so this gate governs visibility of the section, never the actions.
export function isOrganizer(user: CurrentUserDto | null): boolean {
	return user?.role === 'organizer';
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

export function canManageUsers(user: CurrentUserDto | null): boolean {
	return hasPermission(user, USERS_MANAGE);
}

// Handing out permissions takes the superuser grant itself: whoever may grant
// them can give any of them to a second account of their own.
export function canManagePermissions(user: CurrentUserDto | null): boolean {
	return hasPermission(user, WILDCARD);
}

// A Record over the generated union, so a permission the backend adds fails
// `pnpm check` here until it has a label. Insertion order is display order.
export const PERMISSION_LABELS: Record<Permission, string> = {
	'*': 'Полный доступ',
	'schedule:manage': 'Управление программой',
	'schedule:import': 'Импорт программы',
	'notifications:send': 'Рассылка уведомлений',
	'settings:manage': 'Настройки фестиваля',
	'tickets:generate': 'Генерация билетов',
	'sync:run': 'Синхронизация',
	'demo:seed': 'Демо-данные',
	'feedback:read': 'Чтение отзывов',
	'voting:manage': 'Управление голосованием',
	'users:read': 'Просмотр пользователей',
	'users:manage': 'Смена ролей пользователей'
};
