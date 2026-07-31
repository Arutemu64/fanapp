import { describe, expect, it } from 'vitest';

import { type ProjectableEvent, projectExpectedStartTimes } from './scheduleTiming';

// Mirrors backend/tests/unit/application/test_schedule_timing.py so the two
// implementations of the ADR-0008 projection can be diffed case by case.
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

describe('projectExpectedStartTimes', () => {
	it('projects nothing when no event is on stage', () => {
		const projected = projectExpectedStartTimes([event('a'), event('b')], {
			transitionBufferSeconds: BUFFER,
			nowMs: ANCHOR_MS
		});

		expect(projected.size).toBe(0);
	});

	it('projects nothing when the current event has no anchor yet', () => {
		const projected = projectExpectedStartTimes([event('a', { isCurrent: true }), event('b')], {
			transitionBufferSeconds: BUFFER,
			nowMs: ANCHOR_MS
		});

		expect(projected.size).toBe(0);
	});

	it('projects forward from the anchor with a buffer between acts', () => {
		const events = [
			event('current', { durationSeconds: 600, isCurrent: true, actualStartTime: ANCHOR }),
			event('second', { durationSeconds: 300 }),
			event('third', { durationSeconds: 120 })
		];

		const projected = projectExpectedStartTimes(events, {
			transitionBufferSeconds: BUFFER,
			nowMs: ANCHOR_MS
		});

		expect(projected.get('current')?.getTime()).toBe(ANCHOR_MS);
		// 600s of current act plus the 60s changeover.
		expect(projected.get('second')?.getTime()).toBe(ANCHOR_MS + 660 * SECOND);
		// Then the second act's 300s plus another 60s.
		expect(projected.get('third')?.getTime()).toBe(ANCHOR_MS + 1020 * SECOND);
	});

	it('gives past and skipped events no projection', () => {
		const events = [
			event('past'),
			event('current', { durationSeconds: 600, isCurrent: true, actualStartTime: ANCHOR }),
			event('skipped', { durationSeconds: 9999, isSkipped: true }),
			event('upcoming', { durationSeconds: 300 })
		];

		const projected = projectExpectedStartTimes(events, {
			transitionBufferSeconds: BUFFER,
			nowMs: ANCHOR_MS
		});

		expect(projected.has('past')).toBe(false);
		expect(projected.has('skipped')).toBe(false);
		// A skipped act consumes no stage time, so upcoming still follows current.
		expect(projected.get('upcoming')?.getTime()).toBe(ANCHOR_MS + 660 * SECOND);
	});

	it('floors an overrunning act at now plus buffer and cascades the drift', () => {
		const events = [
			event('current', { durationSeconds: 600, isCurrent: true, actualStartTime: ANCHOR }),
			event('second', { durationSeconds: 300 }),
			event('third', { durationSeconds: 120 })
		];
		// The act has run 30 minutes against a planned 10.
		const nowMs = ANCHOR_MS + 30 * 60 * SECOND;

		const projected = projectExpectedStartTimes(events, {
			transitionBufferSeconds: BUFFER,
			nowMs
		});

		// This is the case the server snapshot cannot keep up with: the raw
		// projection is already in the past, so it floors to now + buffer.
		expect(projected.get('second')?.getTime()).toBe(nowMs + BUFFER * SECOND);
		// Third cascades from the clamped value, not the stale raw anchor.
		expect(projected.get('third')?.getTime()).toBe(nowMs + (BUFFER + 300 + BUFFER) * SECOND);
	});
});
