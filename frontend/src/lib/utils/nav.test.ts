import { describe, expect, it } from 'vitest';

import { isActivePath, isNavItemActive } from './nav';

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
