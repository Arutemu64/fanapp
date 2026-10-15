import { describe, expect, it } from 'vitest';

import type { ScheduleBlockStartDto } from '#lib/api/generated/index.js';
import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

import { buildScheduleGroups, filterScheduleGroups, type ScheduleNode } from './scheduleGrouping';

function event(
	overrides: Partial<ScheduleEventWithSubscription> & Pick<ScheduleEventWithSubscription, 'id'>
): ScheduleEventWithSubscription {
	return {
		type: 'event',
		number: null,
		title: 'Выступление',
		duration: 300,
		order: 0,
		is_current: false,
		is_skipped: false,
		nomination_title: null,
		position: null,
		user_subscription: null,
		...overrides
	};
}

function block(id: string, title: string): ScheduleBlockStartDto {
	return { type: 'block_start', id, title, order: 0 };
}

// Flatten a grouped tree into a comparable summary so assertions can avoid
// unchecked index access (noUncheckedIndexedAccess) while still pinning shape.
// Interludes summarize to their kind + event id so both node types are visible.
function summarize(nodes: ScheduleNode[]) {
	return nodes.map((node) => {
		if (node.kind === 'interlude') {
			return { kind: 'interlude' as const, eventId: node.event.id };
		}
		return {
			kind: 'block' as const,
			title: node.title,
			eventCount: node.eventCount,
			nominations: node.nominations.map((nomination) => ({
				title: nomination.title,
				eventIds: nomination.events.map((event) => event.id)
			}))
		};
	});
}

describe('buildScheduleGroups', () => {
	it('groups the events after a block start by nomination', () => {
		const schedule = [
			block('a', 'Блок A'),
			event({ id: '1', nomination_title: 'Ном 1' }),
			event({ id: '2', nomination_title: 'Ном 1' }),
			event({ id: '3', nomination_title: 'Ном 2' }),
			block('b', 'Блок B'),
			event({ id: '4', nomination_title: 'Ном 3' })
		];

		expect(summarize(buildScheduleGroups(schedule))).toEqual([
			{
				kind: 'block',
				title: 'Блок A',
				eventCount: 3,
				nominations: [
					{ title: 'Ном 1', eventIds: ['1', '2'] },
					{ title: 'Ном 2', eventIds: ['3'] }
				]
			},
			{
				kind: 'block',
				title: 'Блок B',
				eventCount: 1,
				nominations: [{ title: 'Ном 3', eventIds: ['4'] }]
			}
		]);
	});

	it('keys each block by its block start, so same-titled blocks stay distinct', () => {
		const nodes = buildScheduleGroups([
			block('a1', 'Блок A'),
			event({ id: '1' }),
			block('b', 'Блок B'),
			event({ id: '2' }),
			block('a2', 'Блок A'),
			event({ id: '3' })
		]);

		expect(nodes.map((node) => node.key)).toEqual(['block-a1', 'block-b', 'block-a2']);
	});

	it('lifts the events above the first block start out as interludes', () => {
		const nodes = buildScheduleGroups([
			event({ id: 'opening', nomination_title: 'Осталась зря' }),
			block('a', 'Косплей'),
			event({ id: '1', nomination_title: 'Ном 1' })
		]);

		// A stray nomination on an interlude is ignored — there is no block for it.
		expect(summarize(nodes)).toEqual([
			{ kind: 'interlude', eventId: 'opening' },
			{
				kind: 'block',
				title: 'Косплей',
				eventCount: 1,
				nominations: [{ title: 'Ном 1', eventIds: ['1'] }]
			}
		]);
	});

	it('keeps a nomination-less event inside its block as a null-titled group', () => {
		const nodes = buildScheduleGroups([
			block('a', 'Косплей'),
			event({ id: '1', nomination_title: 'Ном 1' }),
			event({ id: 'break', nomination_title: null, title: 'Перерыв' })
		]);

		expect(summarize(nodes)).toEqual([
			{
				kind: 'block',
				title: 'Косплей',
				eventCount: 2,
				nominations: [
					{ title: 'Ном 1', eventIds: ['1'] },
					{ title: null, eventIds: ['break'] }
				]
			}
		]);
	});

	it('returns no nodes for an empty schedule', () => {
		expect(buildScheduleGroups([])).toEqual([]);
	});
});

describe('filterScheduleGroups', () => {
	const events = [
		event({ id: 'opening', title: 'Открытие' }),
		event({ id: '1', nomination_title: 'Ном 1' }),
		event({ id: '2', nomination_title: 'Ном 2' }),
		event({ id: '3', nomination_title: 'Ном 3' })
	];
	const [opening, first, second, third] = events as [
		ScheduleEventWithSubscription,
		ScheduleEventWithSubscription,
		ScheduleEventWithSubscription,
		ScheduleEventWithSubscription
	];
	const allNodes = buildScheduleGroups([
		opening,
		block('a', 'Блок A'),
		first,
		second,
		block('b', 'Блок B'),
		third,
		block('empty', 'Пустой блок')
	]);

	it('drops emptied nominations and blocks while keeping node keys stable', () => {
		const result = filterScheduleGroups(allNodes, [first]);

		expect(summarize(result)).toEqual([
			{
				kind: 'block',
				title: 'Блок A',
				eventCount: 1,
				nominations: [{ title: 'Ном 1', eventIds: ['1'] }]
			}
		]);
		// The surviving block reuses its pre-filter key so Svelte keeps its rows.
		expect(result.map((node) => node.key)).toEqual(['block-a']);
	});

	it('keeps an interlude only when its event survives the filter', () => {
		expect(summarize(filterScheduleGroups(allNodes, [opening]))).toEqual([
			{ kind: 'interlude', eventId: 'opening' }
		]);
		expect(filterScheduleGroups(allNodes, [first]).some((node) => node.kind === 'interlude')).toBe(
			false
		);
	});

	it('drops a block that holds no events even when nothing is filtered out', () => {
		const result = filterScheduleGroups(allNodes, events);

		expect(result.map((node) => node.key)).toEqual(['interlude-opening', 'block-a', 'block-b']);
	});

	it('returns no nodes when everything is filtered out', () => {
		expect(filterScheduleGroups(allNodes, [])).toEqual([]);
	});
});
