import { describe, expect, it } from 'vitest';

import {
	formatDuration,
	formatFestivalDateTime,
	formatUntil,
	fromEventDateTimeLocal,
	toEventDateTimeLocal
} from './formatters';

// `duration` is seconds everywhere — spreadsheet cell, database column, API
// field — so that a sub-minute act survives the round trip exactly. These cases
// pin that the label reads the value as seconds and never rounds a short act up
// to a whole minute.
describe('formatDuration', () => {
	it('renders a sub-minute act in seconds', () => {
		expect(formatDuration(45)).toBe('45 секунд');
		expect(formatDuration(1)).toBe('1 секунда');
		expect(formatDuration(3)).toBe('3 секунды');
	});

	it('renders whole minutes without a seconds part', () => {
		expect(formatDuration(60)).toBe('1 минута');
		expect(formatDuration(180)).toBe('3 минуты');
		expect(formatDuration(900)).toBe('15 минут');
	});

	it('renders minutes and seconds together', () => {
		expect(formatDuration(90)).toBe('1 минута 30 секунд');
		expect(formatDuration(210)).toBe('3 минуты 30 секунд');
	});

	it('renders an hour or more', () => {
		// The previous implementation took `seconds % 3600` first, so exactly an
		// hour rendered as "0 минут" and 90 minutes as "30 минут".
		expect(formatDuration(3600)).toBe('1 час');
		expect(formatDuration(5400)).toBe('1 час 30 минут');
		expect(formatDuration(7325)).toBe('2 часа 2 минуты 5 секунд');
	});

	it('renders a zero duration rather than an empty label', () => {
		// The database default is 0, so an event can legitimately have no duration.
		expect(formatDuration(0)).toBe('0 секунд');
	});

	it('clamps values that cannot be rendered as a duration', () => {
		expect(formatDuration(-30)).toBe('0 секунд');
		expect(formatDuration(90.4)).toBe('1 минута 30 секунд');
	});
});

// The countdown is a static label re-derived on each schedule reload, so `now`
// is an argument. These cases pin the queue-distance pluralization, the drift
// fallback (a projected start in the past drops the time), and the accusative
// forms "через" requires ("через 1 минуту", not the nominative "1 минута").
describe('formatUntil', () => {
	const NOW = Date.parse('2026-08-22T12:00:00+03:00');
	const MINUTE = 60_000;
	const HOUR = 60 * MINUTE;

	// ISO start time `ms` from NOW, the shape the API sends.
	function startingIn(ms: number): string {
		return new Date(NOW + ms).toISOString();
	}

	it('shows only the queue distance when no start time is projected', () => {
		expect(formatUntil(3, null, NOW)).toBe('Осталось 3 выступления');
		expect(formatUntil(1, null, NOW)).toBe('Осталось 1 выступление');
		expect(formatUntil(5, null, NOW)).toBe('Осталось 5 выступлений');
	});

	it('drops the countdown when the projected start is already in the past', () => {
		// A stale snapshot after drift: the queue distance stays exact, the time doesn't.
		expect(formatUntil(2, startingIn(-MINUTE), NOW)).toBe('Осталось 2 выступления');
	});

	it('appends a spelled-out countdown to the projected start', () => {
		expect(formatUntil(3, startingIn(2 * HOUR + 15 * MINUTE), NOW)).toBe(
			'Осталось 3 выступления · через 2 часа 15 минут'
		);
	});

	it('omits a zero unit', () => {
		expect(formatUntil(3, startingIn(2 * HOUR), NOW)).toBe('Осталось 3 выступления · через 2 часа');
		expect(formatUntil(3, startingIn(15 * MINUTE), NOW)).toBe(
			'Осталось 3 выступления · через 15 минут'
		);
	});

	it('uses accusative plural forms after "через"', () => {
		expect(formatUntil(2, startingIn(HOUR), NOW)).toBe('Осталось 2 выступления · через 1 час');
		expect(formatUntil(2, startingIn(5 * HOUR), NOW)).toBe(
			'Осталось 2 выступления · через 5 часов'
		);
		expect(formatUntil(2, startingIn(MINUTE), NOW)).toBe('Осталось 2 выступления · через 1 минуту');
		expect(formatUntil(2, startingIn(21 * MINUTE), NOW)).toBe(
			'Осталось 2 выступления · через 21 минуту'
		);
	});

	it('collapses a sub-minute countdown', () => {
		expect(formatUntil(2, startingIn(30_000), NOW)).toBe('Осталось 2 выступления · меньше минуты');
	});
});

// festival_start is stored as an instant and shown/edited on the venue clock
// (Europe/Moscow, +03:00). These pin the display copy and the lossless round
// trip through the zone-naive datetime-local input organizers edit it with.
describe('festival start helpers', () => {
	// 2026-08-22 11:30 Moscow, the shipped default, expressed as its UTC instant.
	const START_ISO = '2026-08-22T08:30:00.000Z';

	it('formats the start on the venue clock without a "г." suffix', () => {
		expect(formatFestivalDateTime(START_ISO)).toBe('22 августа 2026, 11:30');
	});

	it('shows the venue wall clock in the datetime-local value', () => {
		expect(toEventDateTimeLocal(START_ISO)).toBe('2026-08-22T11:30');
	});

	it('round-trips a datetime-local value back to the same instant', () => {
		const local = toEventDateTimeLocal(START_ISO);
		expect(new Date(fromEventDateTimeLocal(local)).getTime()).toBe(new Date(START_ISO).getTime());
	});
});
