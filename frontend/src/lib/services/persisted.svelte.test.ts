import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { Persisted } from './persisted.svelte';

// The Vitest runner is Node with no DOM (ADR-0011), so there is no real Web
// Storage. A Map-backed fake stands in for the pass-through cases and a throwing
// fake for the blocked in-app-webview case — mirroring safeStorage.test.ts.
function fakeStorage(): Storage {
	const map = new Map<string, string>();
	return {
		getItem: (k) => map.get(k) ?? null,
		setItem: (k, v) => void map.set(k, v),
		removeItem: (k) => void map.delete(k),
		clear: () => map.clear(),
		key: (i) => [...map.keys()][i] ?? null,
		get length() {
			return map.size;
		}
	};
}

function throwingStorage(): Storage {
	const blocked = () => {
		throw new Error('SecurityError: Access is denied for this document.');
	};
	return {
		getItem: blocked,
		setItem: blocked,
		removeItem: blocked,
		clear: blocked,
		key: blocked,
		get length(): number {
			return blocked();
		}
	};
}

beforeEach(() => {
	globalThis.localStorage = fakeStorage();
	globalThis.sessionStorage = fakeStorage();
});

afterEach(() => {
	// @ts-expect-error clean up the injected globals between tests
	delete globalThis.localStorage;
	// @ts-expect-error clean up the injected globals between tests
	delete globalThis.sessionStorage;
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
		globalThis.localStorage = throwingStorage();
		const pref = new Persisted<string>('theme-mode', 'system');
		expect(pref.current).toBe('system');
		// A write can't persist, but must not throw, and the value still updates.
		expect(() => (pref.current = 'dark')).not.toThrow();
		expect(pref.current).toBe('dark');
	});
});
