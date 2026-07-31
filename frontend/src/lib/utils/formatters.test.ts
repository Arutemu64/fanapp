import { describe, expect, it } from 'vitest';

import { formatApproximateWait, formatDuration, formatUntil } from './formatters';

describe('formatDuration', () => {
	it('keeps sub-minute acts in seconds', () => {
		// The case that motivated the rewrite: a 30-second single defile used to
		// round up to "1 минута".
		expect(formatDuration(30)).toBe('30 секунд');
		expect(formatDuration(1)).toBe('1 секунда');
		expect(formatDuration(3)).toBe('3 секунды');
		expect(formatDuration(59)).toBe('59 секунд');
	});

	it('formats a zero duration rather than emitting an empty label', () => {
		// The column's server default is 0, so an event can genuinely carry it.
		expect(formatDuration(0)).toBe('0 секунд');
	});

	it('uses whole minutes when the duration divides evenly', () => {
		expect(formatDuration(60)).toBe('1 минута');
		expect(formatDuration(180)).toBe('3 минуты');
		expect(formatDuration(900)).toBe('15 минут');
	});

	it('abbreviates a minutes-and-seconds compound', () => {
		expect(formatDuration(90)).toBe('1 мин 30 с');
		expect(formatDuration(3599)).toBe('59 мин 59 с');
	});

	it('does not drop whole hours', () => {
		// The previous implementation took `seconds % 3600` first, so an hour
		// vanished and 3600 rendered as "0 минут".
		expect(formatDuration(3600)).toBe('1 час');
		expect(formatDuration(7200)).toBe('2 часа');
		expect(formatDuration(5400)).toBe('1 ч 30 мин');
	});
});

describe('formatApproximateWait', () => {
	it('rounds to the nearest minute', () => {
		expect(formatApproximateWait(1500)).toBe('25 мин');
		expect(formatApproximateWait(1529)).toBe('25 мин');
		expect(formatApproximateWait(1531)).toBe('26 мин');
	});

	it('floors at one minute so the push copy stays grammatical', () => {
		// Rendered inside «примерно через …», where "меньше минуты" does not fit.
		expect(formatApproximateWait(0)).toBe('1 мин');
		expect(formatApproximateWait(20)).toBe('1 мин');
	});

	it('switches to hours past the hour mark', () => {
		expect(formatApproximateWait(3600)).toBe('1 ч');
		expect(formatApproximateWait(7200)).toBe('2 ч');
		expect(formatApproximateWait(5400)).toBe('1 ч 30 мин');
	});
});

describe('formatUntil', () => {
	it('shows the queue distance alone when there is no wait to report', () => {
		// Nothing on stage yet, so the schedule has no anchor to measure from.
		expect(formatUntil(3, null)).toBe('Через 3 выступления');
	});

	it('appends the approximate wait when one is known', () => {
		expect(formatUntil(3, 1500)).toBe('Через 3 выступления · ≈ 25 мин');
		expect(formatUntil(1, 5400)).toBe('Через 1 выступление · ≈ 1 ч 30 мин');
	});
});
