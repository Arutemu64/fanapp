import type { CurrentUserDto, UserSettingsDto } from '../../src/lib/api/generated/types.gen';
import type { Handlers } from './api';

import { json } from './api';

type User = CurrentUserDto;

const DEFAULT_SETTINGS: UserSettingsDto = {
	receive_all_announcements: true,
	receive_telegram_notifications: true,
	receive_vk_notifications: true
};

function user(overrides: Partial<User> = {}): User {
	return {
		id: '01890000-0000-7000-8000-000000000001',
		number: 482913,
		username: 'ЛунныйЛис07',
		role: 'visitor',
		email: null,
		avatar_seed: 'e2eSeedVisitor',
		has_password: true,
		ticket: null,
		permissions: [],
		settings: DEFAULT_SETTINGS,
		social_identities: [],
		...overrides
	};
}

export function loggedInAs(overrides: Partial<User> = {}): Handlers {
	return { 'GET /me': json<User>(user(overrides)) };
}

export function organizer(overrides: Partial<User> = {}): Handlers {
	return loggedInAs({
		role: 'organizer',
		username: 'ВажныйФилин01',
		permissions: ['*'],
		...overrides
	});
}
