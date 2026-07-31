import { describe, expect, it } from 'vitest';

import { formatDuration } from './formatters';

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
