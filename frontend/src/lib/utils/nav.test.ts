import { resolve } from '$app/paths';
import { describe, expect, it, vi } from 'vitest';

import { resolvePath } from '#lib/utils/paths.js';

import {
	handleNavItemClick,
	hasUpdateDot,
	isActivePath,
	isNavItemActive,
	tabHref,
	toAppPath
} from './nav';

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

describe('handleNavItemClick', () => {
	// The unit tier runs in Node, which has no MouseEvent; the helper only calls preventDefault.
	function clickEvent() {
		const preventDefault = vi.fn();
		return { event: { preventDefault } as unknown as MouseEvent, preventDefault };
	}

	it('scrolls to top instead of navigating on a re-tap of the current root', () => {
		const { event, preventDefault } = clickEvent();
		const scrollToTop = vi.fn();
		handleNavItemClick(event, resolve('schedule'), 'schedule', scrollToTop);
		expect(preventDefault).toHaveBeenCalledOnce();
		expect(scrollToTop).toHaveBeenCalledOnce();
	});

	it('navigates from a nested page of the same tab', () => {
		const { event, preventDefault } = clickEvent();
		const scrollToTop = vi.fn();
		handleNavItemClick(event, resolve('schedule') + '/changes', 'schedule', scrollToTop);
		expect(preventDefault).not.toHaveBeenCalled();
		expect(scrollToTop).not.toHaveBeenCalled();
	});
});

describe('tabHref', () => {
	it('reopens the query the tab was left at', () => {
		const lastSearches = { [resolve('schedule')]: '?scope=mine' };
		expect(tabHref('schedule', lastSearches)).toBe(`${resolve('schedule')}?scope=mine`);
	});

	it('is the bare root for a tab with nothing remembered', () => {
		expect(tabHref('map', {})).toBe(resolve('map'));
	});
});

describe('hasUpdateDot', () => {
	it('marks only Profile, and only when an update is available', () => {
		expect(hasUpdateDot('profile', true)).toBe(true);
		expect(hasUpdateDot('profile', false)).toBe(false);
		expect(hasUpdateDot('schedule', true)).toBe(false);
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
		expect(resolvePath(toAppPath('/schedule/changes'))).toBe('/schedule/changes');
		expect(resolvePath(toAppPath('/'))).toBe('/');
	});
});
