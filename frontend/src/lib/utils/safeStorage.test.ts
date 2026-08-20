import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { readStorage, removeStorage, writeStorage } from './safeStorage';

// The Vitest runner is Node with no DOM (ADR-0011), so there is no real Web
// Storage to exercise. A Map-backed fake stands in for the pass-through cases;
// a throwing fake stands in for the in-app-webview case this module guards.
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

describe('safeStorage', () => {
	it('reads and writes through to the real storage', () => {
		expect(writeStorage('local', 'k', 'v')).toBe(true);
		expect(readStorage('local', 'k')).toBe('v');
	});

	it('keeps local and session storage separate', () => {
		writeStorage('local', 'k', 'local');
		writeStorage('session', 'k', 'session');
		expect(readStorage('local', 'k')).toBe('local');
		expect(readStorage('session', 'k')).toBe('session');
	});

	it('returns null for a missing key', () => {
		expect(readStorage('session', 'absent')).toBeNull();
	});

	it('removes a key', () => {
		writeStorage('local', 'k', 'v');
		removeStorage('local', 'k');
		expect(readStorage('local', 'k')).toBeNull();
	});

	// The whole reason this module exists: in-app webviews throw on access.
	// Failure must degrade to null / false, never propagate.
	it('returns null when a read throws (storage blocked)', () => {
		globalThis.localStorage = throwingStorage();
		expect(readStorage('local', 'k')).toBeNull();
	});

	it('returns false when a write throws (storage blocked)', () => {
		globalThis.localStorage = throwingStorage();
		expect(writeStorage('local', 'k', 'v')).toBe(false);
	});

	it('does not throw when a remove throws (storage blocked)', () => {
		globalThis.localStorage = throwingStorage();
		expect(() => removeStorage('local', 'k')).not.toThrow();
	});
});
