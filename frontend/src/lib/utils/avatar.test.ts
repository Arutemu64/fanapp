import { describe, expect, it } from 'vitest';

import { createAvatarSeed, getAvatarDataUri } from './avatar';

describe('createAvatarSeed', () => {
	it('matches the backend seed pattern', () => {
		expect(createAvatarSeed()).toMatch(/^[A-Za-z0-9_-]{4,32}$/);
	});

	it('differs between calls', () => {
		expect(createAvatarSeed()).not.toBe(createAvatarSeed());
	});
});

describe('getAvatarDataUri', () => {
	it('draws the same face for the same seed and another for a different one', () => {
		expect(getAvatarDataUri('seed-a')).toBe(getAvatarDataUri('seed-a'));
		expect(getAvatarDataUri('seed-a')).not.toBe(getAvatarDataUri('seed-b'));
	});

	it('returns an SVG data URI', () => {
		expect(getAvatarDataUri('seed-a')).toMatch(/^data:image\/svg\+xml/);
	});
});

describe('getAvatarDataUri cache', () => {
	it('keeps returning correct faces after far more seeds than it caches', () => {
		const first = getAvatarDataUri('bounded-0');
		for (let i = 1; i < 500; i++) getAvatarDataUri(`bounded-${i}`);
		expect(getAvatarDataUri('bounded-0')).toBe(first);
	});
});
