import type { ApiSchemas, Handlers } from './api';

import { json } from './api';

type User = ApiSchemas['CurrentUserDTO'];

const DEFAULT_SETTINGS: ApiSchemas['UserSettingsDTO'] = {
	receive_all_announcements: true,
	receive_telegram_notifications: true,
	receive_vk_notifications: true
};

/** Build a valid CurrentUserDTO; override any field per test. */
export function user(overrides: Partial<User> = {}): User {
	return {
		id: '01890000-0000-7000-8000-000000000001',
		username: 'test_visitor',
		role: 'visitor',
		email: null,
		has_password: true,
		ticket: null,
		permissions: [],
		settings: DEFAULT_SETTINGS,
		social_identities: [],
		...overrides
	};
}

/** Handlers that log the given user in (replaces the guest `GET /me/`). */
export function loggedInAs(overrides: Partial<User> = {}): Handlers {
	return { 'GET /me/': json<User>(user(overrides)) };
}

/** An organiser with full permissions — for tools/ and other gated surfaces. */
export function organizer(overrides: Partial<User> = {}): Handlers {
	return loggedInAs({ role: 'org', username: 'test_org', permissions: ['*'], ...overrides });
}
