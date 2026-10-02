import { fakeStorage, throwingStorage } from '$lib/testing/storage';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Persisted } from './persisted.svelte';

beforeEach(() => {
	vi.stubGlobal('localStorage', fakeStorage());
	vi.stubGlobal('sessionStorage', fakeStorage());
});

describe('Persisted', () => {
	it('uses the fallback when nothing is stored', () => {
		const pref = new Persisted('missing', 'system');
		expect(pref.current).toBe('system');
	});

	it('seeds from a previously stored value', () => {
		localStorage.setItem('theme-mode', 'dark');
		const pref = new Persisted('theme-mode', 'system');
		expect(pref.current).toBe('dark');
	});

	it('writes through to storage on assignment', () => {
		const pref = new Persisted<string>('theme-mode', 'system');
		pref.current = 'light';
		expect(pref.current).toBe('light');
		expect(localStorage.getItem('theme-mode')).toBe('light');
	});

	it('falls back when the stored value fails parse', () => {
		localStorage.setItem('theme-mode', 'neon');
		const parse = (raw: string) => (raw === 'light' || raw === 'dark' ? raw : undefined);
		const pref = new Persisted<'light' | 'dark'>('theme-mode', 'dark', { parse });
		expect(pref.current).toBe('dark');
	});

	it('honours the session storage kind', () => {
		const pref = new Persisted<string>('marker', 'a', { kind: 'session' });
		pref.current = 'b';
		expect(sessionStorage.getItem('marker')).toBe('b');
		expect(localStorage.getItem('marker')).toBeNull();
	});

	it('degrades to an in-memory value when storage is blocked', () => {
		vi.stubGlobal('localStorage', throwingStorage());
		const pref = new Persisted<string>('theme-mode', 'system');
		expect(pref.current).toBe('system');
		// A write can't persist, but must not throw, and the value still updates.
		expect(() => (pref.current = 'dark')).not.toThrow();
		expect(pref.current).toBe('dark');
	});
});
