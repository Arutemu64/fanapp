import { describe, expect, it } from 'vitest';

import { getFestivalPhase, nextBoundary } from './festivalPhase';

describe('getFestivalPhase', () => {
	const start = 1_000;
	const end = 2_000;

	it('flips at each boundary instant', () => {
		expect(getFestivalPhase(999, start, end)).toBe('before');
		expect(getFestivalPhase(1_000, start, end)).toBe('during');
		expect(getFestivalPhase(1_999, start, end)).toBe('during');
		expect(getFestivalPhase(2_000, start, end)).toBe('after');
	});
});

describe('nextBoundary', () => {
	it('picks the earliest boundary still ahead', () => {
		expect(nextBoundary([3_000, 500, 2_000], 1_000)).toBe(2_000);
	});

	it('skips passed and missing boundaries', () => {
		expect(nextBoundary([1_000, Number.NaN, 4_000], 1_000)).toBe(4_000);
		expect(nextBoundary([500, Number.NaN], 1_000)).toBeNull();
	});
});
