import { describe, expect, it } from 'vitest';

import type { CurrentUserDto } from '#lib/api/generated/index.js';

import { requireTool, toolsFor } from './tools';

function userWith(permissions: CurrentUserDto['permissions']): CurrentUserDto {
	return { permissions } as CurrentUserDto;
}

const questOn = { quest_enabled: true };
const questOff = { quest_enabled: false };

function keys(user: CurrentUserDto | null, config = questOn) {
	return toolsFor(user, config).map((tool) => tool.key);
}

describe('toolsFor', () => {
	it('lists nothing for a guest', () => {
		expect(keys(null)).toEqual([]);
	});

	it('lists nothing for a holder of a permission that opens no tool', () => {
		expect(keys(userWith(['schedule:manage', 'demo:seed']))).toEqual([]);
	});

	it('lists only the tools whose permission is held', () => {
		expect(keys(userWith(['sync:run', 'feedback:read']))).toEqual(['tickets', 'sync', 'feedback']);
	});

	it('lists every tool for the wildcard holder, in dashboard order', () => {
		expect(keys(userWith(['*']))).toEqual([
			'settings',
			'voting',
			'import-schedule',
			'broadcast',
			'tickets',
			'sync',
			'feedback',
			'users',
			'quest'
		]);
	});

	it.each(['quest:award', 'quest:manage'] as const)('opens the quest tool for %s', (permission) => {
		expect(keys(userWith([permission]))).toEqual(['quest']);
	});

	it('hides the quest tool while the quest is off', () => {
		expect(keys(userWith(['*']), questOff)).not.toContain('quest');
	});
});

describe('requireTool', () => {
	it('lets a holder through', () => {
		expect(() => requireTool('sync', userWith(['sync:run']), questOn)).not.toThrow();
	});

	it('rejects a user without the permission', () => {
		expect(() => requireTool('sync', userWith(['feedback:read']), questOn)).toThrow();
	});

	it('rejects the quest tool while the quest is off', () => {
		expect(() => requireTool('quest', userWith(['quest:award']), questOff)).toThrow();
	});
});
