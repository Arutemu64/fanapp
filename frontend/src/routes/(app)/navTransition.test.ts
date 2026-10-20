import { describe, expect, it } from 'vitest';

import { navTransitionKind } from './navTransition';

const tabRoots = new Set(['/', '/schedule', '/voting', '/map', '/profile']);

function kind(from: string, to: string, fromBackHref?: string) {
	return navTransitionKind({ from, to, fromBackHref, tabRoots });
}

describe('navTransitionKind', () => {
	it('skips a same-path navigation', () => {
		expect(kind('/schedule', '/schedule')).toBeNull();
	});

	it('fades between tabs', () => {
		expect(kind('/schedule', '/voting')).toBe('fade');
		expect(kind('/', '/profile')).toBe('fade');
	});

	it('slides forward into a deeper page', () => {
		expect(kind('/voting', '/voting/cosplay')).toBe('forward');
		expect(kind('/', '/schedule/changes')).toBe('forward');
	});

	it('slides back to a shallower page', () => {
		expect(kind('/tools/users/7', '/tools')).toBe('back');
	});

	it('slides back to the declared parent even at equal depth', () => {
		expect(kind('/tools', '/profile', '/profile')).toBe('back');
	});

	it('fades between siblings at one depth', () => {
		expect(kind('/tools/users/7', '/tools/users/8')).toBe('fade');
	});
});
