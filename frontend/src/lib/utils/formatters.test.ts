import { describe, expect, it } from 'vitest';

import { m } from '#lib/paraglide/messages.js';

import {
	formatDayHeading,
	formatDuration,
	formatEventNumber,
	formatFestivalDateTime,
	formatRelativeTime,
	formatUntil,
	fromEventDateTimeLocal,
	previousDayKey,
	toEventDateTimeLocal
} from './formatters';

describe('formatEventNumber', () => {
	it('pads the public number to three digits', () => {
		expect(formatEventNumber(7)).toBe('007');
		expect(formatEventNumber(1234)).toBe('1234');
	});

	it('returns null for a numberless row', () => {
		expect(formatEventNumber(null)).toBeNull();
		expect(formatEventNumber(undefined)).toBeNull();
	});
});

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
		// Pins the hour carry: taking `seconds % 3600` first renders exactly an
		// hour as "0 минут" and 90 minutes as "30 минут".
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

// The label is just the position distance ("how many acts away") — the schedule
// carries no predicted clock time (ADR-0014). These cases pin the three-form
// Russian pluralization of the distance.
describe('formatUntil', () => {
	it('pluralizes the position distance', () => {
		expect(formatUntil(1)).toBe('Осталось 1 выступление');
		expect(formatUntil(3)).toBe('Осталось 3 выступления');
		expect(formatUntil(5)).toBe('Осталось 5 выступлений');
	});
});

// festival_start is stored as an instant and shown/edited on the venue clock
// (Europe/Moscow, +03:00). These pin the display copy and the lossless round
// trip through the zone-naive datetime-local input organizers edit it with.
describe('festival start helpers', () => {
	// 2027-03-17 11:30 Moscow, the shipped default, expressed as its UTC instant.
	const START_ISO = '2027-03-17T08:30:00.000Z';

	it('formats the start on the venue clock without a "г." suffix', () => {
		expect(formatFestivalDateTime(START_ISO)).toBe('17 марта 2027, 11:30');
	});

	it('shows the venue wall clock in the datetime-local value', () => {
		expect(toEventDateTimeLocal(START_ISO)).toBe('2027-03-17T11:30');
	});

	it('round-trips a datetime-local value back to the same instant', () => {
		const local = toEventDateTimeLocal(START_ISO);
		expect(new Date(fromEventDateTimeLocal(local)).getTime()).toBe(new Date(START_ISO).getTime());
	});
});

// The messages pick their form with Intl.PluralRules('ru') (CLDR), not mod-10
// arithmetic: 11–14 are `many` even though they end in 1–4. `other` is fractions
// only and takes the `few` form ("1,5 часа").
describe('Russian plural messages', () => {
	it.each([
		[0, '0 голосов'],
		[1, '1 голос'],
		[2, '2 голоса'],
		[5, '5 голосов'],
		[11, '11 голосов'],
		[12, '12 голосов'],
		[21, '21 голос'],
		[22, '22 голоса'],
		[25, '25 голосов'],
		[111, '111 голосов'],
		[1.5, '1.5 голоса']
	])('%d → %s', (count, expected) => {
		expect(m.votes_count({ count })).toBe(expected);
	});
});

// The venue clock is Europe/Moscow (UTC+3, no DST) when PUBLIC_TIMEZONE is unset,
// so these instants are written in UTC with the venue-local time alongside.
describe('formatRelativeTime', () => {
	const now = Date.parse('2026-10-08T12:00:00Z');

	it('reads against the clock it is given, so a ticking caller re-labels', () => {
		const createdAt = '2026-10-08T11:59:30Z';
		expect(formatRelativeTime(createdAt, now)).toBe('только что');
		expect(formatRelativeTime(createdAt, now + 5 * 60_000)).toBe('5 минут назад');
	});

	it('falls back to the venue date and time after a day', () => {
		expect(formatRelativeTime('2026-10-06T09:30:00Z', now)).toBe('06.10.2026, 12:30');
	});
});

describe('formatDayHeading', () => {
	// 00:30 at the venue on 8 October, while it is still 7 October in UTC.
	const now = Date.parse('2026-10-07T21:30:00Z');

	it('names today and yesterday on the venue clock, not the device one', () => {
		expect(formatDayHeading('2026-10-07T21:10:00Z', now)).toBe('Сегодня');
		expect(formatDayHeading('2026-10-07T20:50:00Z', now)).toBe('Вчера');
	});

	it('spells out older days, adding the year only when it differs', () => {
		expect(formatDayHeading('2026-10-01T10:00:00Z', now)).toBe('1 октября');
		expect(formatDayHeading('2025-12-31T10:00:00Z', now)).toBe('31 декабря 2025');
	});
});

describe('previousDayKey', () => {
	it('steps back one calendar day across month and year boundaries', () => {
		expect(previousDayKey('2026-10-08')).toBe('2026-10-07');
		expect(previousDayKey('2026-03-01')).toBe('2026-02-28');
		expect(previousDayKey('2024-03-01')).toBe('2024-02-29');
		expect(previousDayKey('2026-01-01')).toBe('2025-12-31');
	});

	it('is pure date arithmetic, so a DST switch cannot skip a day', () => {
		// Europe/Berlin springs forward on 29 March 2026: "now minus 24h" at 00:30
		// on the 30th would land on the 28th.
		expect(previousDayKey('2026-03-30')).toBe('2026-03-29');
	});
});
