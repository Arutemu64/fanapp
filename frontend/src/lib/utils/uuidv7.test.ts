import { describe, expect, it } from 'vitest';

import { uuidv7 } from './uuidv7.js';

describe('uuidv7', () => {
	it('sets the version and variant bits', () => {
		expect(uuidv7()).toMatch(
			/^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
		);
	});

	it('encodes the millisecond timestamp in the first 48 bits', () => {
		const now = Date.UTC(2026, 9, 16, 12, 0, 0, 123);

		const hex = uuidv7(now).replaceAll('-', '').slice(0, 12);

		expect(Number.parseInt(hex, 16)).toBe(now);
	});

	it('sorts by creation time', () => {
		const earlier = uuidv7(1_000);
		const later = uuidv7(2_000);

		expect(earlier < later).toBe(true);
	});
});
