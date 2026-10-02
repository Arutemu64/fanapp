import { fakeStorage, throwingStorage } from '$lib/testing/storage';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { readStorage, removeStorage, writeStorage } from './safeStorage';

beforeEach(() => {
	vi.stubGlobal('localStorage', fakeStorage());
	vi.stubGlobal('sessionStorage', fakeStorage());
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
		vi.stubGlobal('localStorage', throwingStorage());
		expect(readStorage('local', 'k')).toBeNull();
	});

	it('returns false when a write throws (storage blocked)', () => {
		vi.stubGlobal('localStorage', throwingStorage());
		expect(writeStorage('local', 'k', 'v')).toBe(false);
	});

	it('does not throw when a remove throws (storage blocked)', () => {
		vi.stubGlobal('localStorage', throwingStorage());
		expect(() => removeStorage('local', 'k')).not.toThrow();
	});
});
