import { beforeEach, describe, expect, it, vi } from 'vitest';

import { fakeStorage, throwingStorage } from '#lib/testing/storage.js';

import { usePersisted } from './usePersisted';

beforeEach(() => {
	vi.stubGlobal('localStorage', fakeStorage());
	vi.stubGlobal('sessionStorage', fakeStorage());
});

describe('usePersisted', () => {
	it('uses the fallback when nothing is stored', () => {
		const pref = usePersisted('missing', 'system');
		expect(pref.value).toBe('system');
	});

	it('seeds from a previously stored value', () => {
		localStorage.setItem('theme-mode', 'dark');
		const pref = usePersisted('theme-mode', 'system');
		expect(pref.value).toBe('dark');
	});

	it('writes through to storage on assignment', () => {
		const pref = usePersisted<string>('theme-mode', 'system');
		pref.value = 'light';
		expect(pref.value).toBe('light');
		expect(localStorage.getItem('theme-mode')).toBe('light');
	});

	it('falls back when the stored value fails parse', () => {
		localStorage.setItem('theme-mode', 'neon');
		const parse = (raw: string) => (raw === 'light' || raw === 'dark' ? raw : undefined);
		const pref = usePersisted<'light' | 'dark'>('theme-mode', 'dark', { parse });
		expect(pref.value).toBe('dark');
	});

	it('honours the session storage kind', () => {
		const pref = usePersisted<string>('marker', 'a', { kind: 'session' });
		pref.value = 'b';
		expect(sessionStorage.getItem('marker')).toBe('b');
		expect(localStorage.getItem('marker')).toBeNull();
	});

	it('degrades to an in-memory value when storage is blocked', () => {
		vi.stubGlobal('localStorage', throwingStorage());
		const pref = usePersisted<string>('theme-mode', 'system');
		expect(pref.value).toBe('system');
		// A write can't persist, but must not throw, and the value still updates.
		expect(() => (pref.value = 'dark')).not.toThrow();
		expect(pref.value).toBe('dark');
	});
});
