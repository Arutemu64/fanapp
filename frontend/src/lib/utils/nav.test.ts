import { resolve } from '$app/paths';
import { describe, expect, it } from 'vitest';

import { isActivePath, isNavItemActive, toAppPath } from './nav';

describe('isActivePath', () => {
	it.each([
		['/', '/', true],
		['/program', '/', false],
		['/program', '/program', true],
		['/program/42', '/program', true],
		['/program/', '/program', true],
		['/programme', '/program', false],
		['/prog', '/program', false]
	])('%s against %s -> %s', (activeUrl, href, expected) => {
		expect(isActivePath(activeUrl, href)).toBe(expected);
	});
});

describe('isNavItemActive', () => {
	const profile = { href: 'profile', nestedRoots: ['feedback', 'tools'] } as const;

	it.each([
		['/profile', true],
		['/profile/ticket', true],
		['/feedback', true],
		['/tools/users/42', true],
		['/toolsets', false],
		['/schedule', false]
	])('%s -> %s', (activeUrl, expected) => {
		expect(isNavItemActive(activeUrl, profile)).toBe(expected);
	});

	it('falls back to the item href alone without nested roots', () => {
		expect(isNavItemActive('/map', { href: 'map' })).toBe(true);
		expect(isNavItemActive('/feedback', { href: 'map' })).toBe(false);
	});
});

describe('toAppPath', () => {
	// Paths the backend's notification interactors actually send.
	it.each([
		['/', ''],
		['/notifications', 'notifications'],
		['/schedule', 'schedule'],
		['/schedule/changes', 'schedule/changes']
	])('%s -> %s', (backendPath, expected) => {
		expect(toAppPath(backendPath)).toBe(expected);
	});

	it('resolves to the same pathname the backend named', () => {
		expect(resolve(toAppPath('/schedule/changes'))).toBe('/schedule/changes');
		expect(resolve(toAppPath('/'))).toBe('/');
	});
});
