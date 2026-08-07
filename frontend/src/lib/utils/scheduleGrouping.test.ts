import type { ScheduleEventWithSubscription } from '$lib/types/schedule';

import { describe, expect, it } from 'vitest';

import { buildScheduleGroups, filterScheduleGroups } from './scheduleGrouping';

function event(
	overrides: Partial<ScheduleEventWithSubscription> & Pick<ScheduleEventWithSubscription, 'id'>
): ScheduleEventWithSubscription {
	return {
		number: null,
		title: 'Выступление',
		duration: 300,
		order: 0,
		is_current: false,
		is_skipped: false,
		nomination_title: null,
		block_title: null,
		queue: null,
		user_subscription: null,
		...overrides
	};
}

// Flatten a grouped tree into a comparable summary so assertions can avoid
// unchecked index access (noUncheckedIndexedAccess) while still pinning shape.
function summarize(groups: ReturnType<typeof buildScheduleGroups>) {
	return groups.map((block) => ({
		title: block.title,
		eventCount: block.eventCount,
		nominations: block.nominations.map((nomination) => ({
			title: nomination.title,
			eventIds: nomination.events.map((event) => event.id)
		}))
	}));
}

describe('buildScheduleGroups', () => {
	it('groups consecutive rows by block, then nomination', () => {
		const schedule = [
			event({ id: '1', block_title: 'Блок A', nomination_title: 'Ном 1' }),
			event({ id: '2', block_title: 'Блок A', nomination_title: 'Ном 1' }),
			event({ id: '3', block_title: 'Блок A', nomination_title: 'Ном 2' }),
			event({ id: '4', block_title: 'Блок B', nomination_title: 'Ном 3' })
		];

		expect(summarize(buildScheduleGroups(schedule))).toEqual([
			{
				title: 'Блок A',
				eventCount: 3,
				nominations: [
					{ title: 'Ном 1', eventIds: ['1', '2'] },
					{ title: 'Ном 2', eventIds: ['3'] }
				]
			},
			{
				title: 'Блок B',
				eventCount: 1,
				nominations: [{ title: 'Ном 3', eventIds: ['4'] }]
			}
		]);
	});

	it('starts a new block group when the same title reappears non-consecutively', () => {
		const groups = buildScheduleGroups([
			event({ id: '1', block_title: 'Блок A' }),
			event({ id: '2', block_title: 'Блок B' }),
			event({ id: '3', block_title: 'Блок A' })
		]);

		expect(groups.map((g) => g.title)).toEqual(['Блок A', 'Блок B', 'Блок A']);
		// Keys are positional, so the two "Блок A" runs stay distinct sections.
		expect(new Set(groups.map((g) => g.key)).size).toBe(3);
	});

	it('falls back to placeholder titles for null/blank block and nomination', () => {
		expect(
			summarize(
				buildScheduleGroups([event({ id: '1', block_title: null, nomination_title: '   ' })])
			)
		).toEqual([
			{
				title: 'Без блока',
				eventCount: 1,
				nominations: [{ title: 'Без номинации', eventIds: ['1'] }]
			}
		]);
	});

	it('returns no groups for an empty schedule', () => {
		expect(buildScheduleGroups([])).toEqual([]);
	});
});

describe('filterScheduleGroups', () => {
	const schedule = [
		event({ id: '1', block_title: 'Блок A', nomination_title: 'Ном 1' }),
		event({ id: '2', block_title: 'Блок A', nomination_title: 'Ном 2' }),
		event({ id: '3', block_title: 'Блок B', nomination_title: 'Ном 3' })
	];
	const allGroups = buildScheduleGroups(schedule);

	it('drops emptied nominations and blocks while keeping group keys stable', () => {
		const filtered = schedule.filter((e) => e.id === '1');

		const result = filterScheduleGroups(allGroups, filtered);

		expect(summarize(result)).toEqual([
			{
				title: 'Блок A',
				eventCount: 1,
				nominations: [{ title: 'Ном 1', eventIds: ['1'] }]
			}
		]);
		// The surviving block reuses its pre-filter key so Svelte keeps its rows.
		expect(result.map((g) => g.key)).toEqual(
			allGroups.filter((g) => g.title === 'Блок A').map((g) => g.key)
		);
	});

	it('returns every group unchanged when nothing is filtered out', () => {
		expect(summarize(filterScheduleGroups(allGroups, schedule))).toEqual(summarize(allGroups));
	});

	it('returns no groups when everything is filtered out', () => {
		expect(filterScheduleGroups(allGroups, [])).toEqual([]);
	});
});
