import { FESTIVAL_START } from '$lib/constants/festival';
import { describe, expect, it } from 'vitest';

import { resolveFestivalPhase } from './festival';

const BEFORE = FESTIVAL_START - 60_000;
const AFTER = FESTIVAL_START + 60_000;

function event(overrides: Partial<Parameters<typeof resolveFestivalPhase>[0][number]> = {}) {
	return {
		actual_start_time: null,
		is_current: false,
		is_skipped: false,
		...overrides
	};
}

describe('resolveFestivalPhase', () => {
	it('is "before" ahead of the announced start with an untouched schedule', () => {
		expect(resolveFestivalPhase([event(), event()], BEFORE)).toBe('before');
	});

	it('is "before" ahead of the announced start with no schedule imported yet', () => {
		expect(resolveFestivalPhase([], BEFORE)).toBe('before');
	});

	it('is "live" past the announced start even before the first act is marked', () => {
		expect(resolveFestivalPhase([event()], AFTER)).toBe('live');
	});

	it('is "live" whenever an act is marked as current, even ahead of the clock', () => {
		// Organizers running early outrank the date written months ago.
		expect(resolveFestivalPhase([event({ is_current: true }), event()], BEFORE)).toBe('live');
	});

	it('is "live" while some acts have run and others have not', () => {
		const schedule = [event({ actual_start_time: '2026-08-22T09:00:00Z' }), event()];

		expect(resolveFestivalPhase(schedule, AFTER)).toBe('live');
	});

	it('is "after" once every act has run and none is on stage', () => {
		const schedule = [
			event({ actual_start_time: '2026-08-22T09:00:00Z' }),
			event({ actual_start_time: '2026-08-22T09:20:00Z' })
		];

		expect(resolveFestivalPhase(schedule, AFTER)).toBe('after');
	});

	it('ignores skipped acts when deciding the programme is over', () => {
		const schedule = [
			event({ actual_start_time: '2026-08-22T09:00:00Z' }),
			event({ is_skipped: true })
		];

		expect(resolveFestivalPhase(schedule, AFTER)).toBe('after');
	});
});
