import { describe, expect, it } from 'vitest';

import { type ProjectableEvent, projectSecondsUntil } from './scheduleTiming';

// Mirrors backend/tests/unit/application/test_schedule_timing.py so the two
// implementations of the ADR-0013 projection can be diffed case by case.
const ANCHOR = '2026-07-09T12:00:00+00:00';
const ANCHOR_MS = Date.parse(ANCHOR);
const BUFFER = 60;
const SECOND = 1000;

function event(
	id: string,
	{
		durationSeconds = 600,
		isCurrent = false,
		isSkipped = false,
		actualStartTime = null
	}: {
		durationSeconds?: number;
		isCurrent?: boolean;
		isSkipped?: boolean;
		actualStartTime?: string | null;
	} = {}
): ProjectableEvent {
	return {
		id,
		duration_seconds: durationSeconds,
		is_current: isCurrent,
		is_skipped: isSkipped,
		actual_start_time: actualStartTime
	};
}

describe('projectSecondsUntil', () => {
	it('projects nothing when no event is on stage', () => {
		const waits = projectSecondsUntil([event('a'), event('b')], {
			transitionBufferSeconds: BUFFER,
			nowMs: ANCHOR_MS
		});

		expect(waits.size).toBe(0);
	});

	it('projects nothing when the current event has no anchor yet', () => {
		const waits = projectSecondsUntil([event('a', { isCurrent: true }), event('b')], {
			transitionBufferSeconds: BUFFER,
			nowMs: ANCHOR_MS
		});

		expect(waits.size).toBe(0);
	});

	it('measures from what is left of the act on stage', () => {
		const events = [
			event('current', { durationSeconds: 600, isCurrent: true, actualStartTime: ANCHOR }),
			event('second', { durationSeconds: 300 }),
			event('third', { durationSeconds: 120 })
		];

		const waits = projectSecondsUntil(events, {
			transitionBufferSeconds: BUFFER,
			nowMs: ANCHOR_MS
		});

		// Nothing to report for the act already on stage.
		expect(waits.has('current')).toBe(false);
		// All 600s of the current act still to run, plus the changeover.
		expect(waits.get('second')).toBe(660);
		// Then the second act's 300s and another changeover.
		expect(waits.get('third')).toBe(1020);
	});

	it('counts down as the current act runs', () => {
		const events = [
			event('current', { durationSeconds: 600, isCurrent: true, actualStartTime: ANCHOR }),
			event('second', { durationSeconds: 300 })
		];

		const waits = projectSecondsUntil(events, {
			transitionBufferSeconds: BUFFER,
			// Four minutes into the act, so 360s of it are left.
			nowMs: ANCHOR_MS + 240 * SECOND
		});

		expect(waits.get('second')).toBe(420);
	});

	it('gives past and skipped events no wait', () => {
		const events = [
			event('past'),
			event('current', { durationSeconds: 600, isCurrent: true, actualStartTime: ANCHOR }),
			event('skipped', { durationSeconds: 9999, isSkipped: true }),
			event('upcoming', { durationSeconds: 300 })
		];

		const waits = projectSecondsUntil(events, {
			transitionBufferSeconds: BUFFER,
			nowMs: ANCHOR_MS
		});

		expect(waits.has('past')).toBe(false);
		expect(waits.has('skipped')).toBe(false);
		// A skipped act takes no stage time, so upcoming still follows current.
		expect(waits.get('upcoming')).toBe(660);
	});

	it('never reports a negative wait once an act overruns', () => {
		const events = [
			event('current', { durationSeconds: 600, isCurrent: true, actualStartTime: ANCHOR }),
			event('second', { durationSeconds: 300 }),
			event('third', { durationSeconds: 120 })
		];
		// The act has run 30 minutes against a planned 10.
		const nowMs = ANCHOR_MS + 30 * 60 * SECOND;

		const waits = projectSecondsUntil(events, { transitionBufferSeconds: BUFFER, nowMs });

		// The overrunning act owes no more stage time, but the changeover remains.
		expect(waits.get('second')).toBe(BUFFER);
		// Third follows on from that, not from the original plan.
		expect(waits.get('third')).toBe(BUFFER + 300 + BUFFER);
	});
});
