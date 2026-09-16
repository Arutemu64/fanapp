import type { CurrentUserDto } from '$lib/api/generated';

import { describe, expect, it } from 'vitest';

import { hasPermission } from './permissions';

function userWith(permissions: CurrentUserDto['permissions']): CurrentUserDto {
	return { permissions } as CurrentUserDto;
}

describe('hasPermission', () => {
	it('returns false when there is no user', () => {
		expect(hasPermission(null, 'sync:run')).toBe(false);
	});

	it('grants a specific permission the user holds', () => {
		expect(hasPermission(userWith(['sync:run']), 'sync:run')).toBe(true);
	});

	it('denies a permission the user does not hold', () => {
		expect(hasPermission(userWith(['sync:run']), 'settings:manage')).toBe(false);
	});

	it('grants every permission to a wildcard holder', () => {
		const superuser = userWith(['*']);
		expect(hasPermission(superuser, 'sync:run')).toBe(true);
		expect(hasPermission(superuser, 'settings:manage')).toBe(true);
	});
});
