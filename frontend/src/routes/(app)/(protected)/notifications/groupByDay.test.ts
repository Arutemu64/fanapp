import { describe, expect, it } from 'vitest';

import { groupByDay } from './groupByDay';

// Venue clock is Europe/Moscow (UTC+3) when PUBLIC_TIMEZONE is unset.
const now = Date.parse('2026-10-08T12:00:00Z');

function item(id: string, createdAt: string) {
	return { id, created_at: createdAt };
}

describe('groupByDay', () => {
	it('splits a newest-first feed into venue-day sections in order', () => {
		const groups = groupByDay(
			[
				item('a', '2026-10-08T10:00:00Z'),
				item('b', '2026-10-07T22:00:00Z'), // 01:00 on 8 October at the venue
				item('c', '2026-10-07T20:00:00Z'),
				item('d', '2026-10-01T10:00:00Z')
			],
			now
		);

		expect(groups.map((group) => group.heading)).toEqual(['Сегодня', 'Вчера', '1 октября']);
		expect(groups.map((group) => group.items.map((entry) => entry.id))).toEqual([
			['a', 'b'],
			['c'],
			['d']
		]);
	});

	it('keeps one section per day even when the merged feed revisits it', () => {
		const groups = groupByDay(
			[
				item('live', '2026-10-08T10:00:00Z'),
				item('older', '2026-10-07T10:00:00Z'),
				item('same-day-again', '2026-10-08T09:00:00Z')
			],
			now
		);

		expect(groups.map((group) => group.key)).toEqual(['2026-10-08', '2026-10-07']);
		expect(groups[0]?.items.map((entry) => entry.id)).toEqual(['live', 'same-day-again']);
	});

	it('returns no sections for an empty feed', () => {
		expect(groupByDay([], now)).toEqual([]);
	});
});
