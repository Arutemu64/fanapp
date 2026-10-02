import { describe, expect, it } from 'vitest';

import { isActivePath } from './nav';

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
