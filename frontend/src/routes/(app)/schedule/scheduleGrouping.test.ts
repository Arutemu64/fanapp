import type { ScheduleEventWithSubscription } from '$lib/types/schedule';

import { describe, expect, it } from 'vitest';

import { buildScheduleGroups, filterScheduleGroups, type ScheduleNode } from './scheduleGrouping';

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
	it('groups consecutive rows by block, then nomination', () => {
		const schedule = [
			event({ id: '1', block_title: 'Блок A', nomination_title: 'Ном 1' }),
			event({ id: '2', block_title: 'Блок A', nomination_title: 'Ном 1' }),
			event({ id: '3', block_title: 'Блок A', nomination_title: 'Ном 2' }),
			event({ id: '4', block_title: 'Блок B', nomination_title: 'Ном 3' })
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

	it('starts a new block group when the same title reappears non-consecutively', () => {
		const nodes = buildScheduleGroups([
			event({ id: '1', block_title: 'Блок A' }),
			event({ id: '2', block_title: 'Блок B' }),
			event({ id: '3', block_title: 'Блок A' })
		]);

		expect(nodes.map((node) => (node.kind === 'block' ? node.title : null))).toEqual([
			'Блок A',
			'Блок B',
			'Блок A'
		]);
		// Keys are positional, so the two "Блок A" runs stay distinct sections.
		expect(new Set(nodes.map((node) => node.key)).size).toBe(3);
	});

	it('lifts a block-less row out as an interlude between block sections', () => {
		const nodes = buildScheduleGroups([
			event({ id: '1', block_title: 'Косплей', nomination_title: 'Ном 1' }),
			event({ id: 'break', block_title: null, nomination_title: null, title: 'Перерыв' }),
			event({ id: '2', block_title: 'Караоке', nomination_title: 'Ном 2' })
		]);

		expect(summarize(nodes)).toEqual([
			{
				kind: 'block',
				title: 'Косплей',
				eventCount: 1,
				nominations: [{ title: 'Ном 1', eventIds: ['1'] }]
			},
			{ kind: 'interlude', eventId: 'break' },
			{
				kind: 'block',
				title: 'Караоке',
				eventCount: 1,
				nominations: [{ title: 'Ном 2', eventIds: ['2'] }]
			}
		]);
	});

	it('treats a blank block as an interlude and ignores a stray nomination on it', () => {
		// A row with no block is an interlude even if it carries a nomination —
		// there is no block for that nomination to sit under.
		const nodes = buildScheduleGroups([
			event({ id: '1', block_title: '   ', nomination_title: 'Осталась зря' })
		]);

		expect(summarize(nodes)).toEqual([{ kind: 'interlude', eventId: '1' }]);
	});

	it('renders a null-titled nomination group for a blank nomination inside a block', () => {
		const nodes = buildScheduleGroups([
			event({ id: '1', block_title: 'Косплей', nomination_title: null })
		]);

		expect(summarize(nodes)).toEqual([
			{
				kind: 'block',
				title: 'Косплей',
				eventCount: 1,
				nominations: [{ title: null, eventIds: ['1'] }]
			}
		]);
	});

	it('returns no nodes for an empty schedule', () => {
		expect(buildScheduleGroups([])).toEqual([]);
	});
});

describe('filterScheduleGroups', () => {
	const schedule = [
		event({ id: '1', block_title: 'Блок A', nomination_title: 'Ном 1' }),
		event({ id: '2', block_title: 'Блок A', nomination_title: 'Ном 2' }),
		event({ id: 'break', block_title: null, title: 'Перерыв' }),
		event({ id: '3', block_title: 'Блок B', nomination_title: 'Ном 3' })
	];
	const allNodes = buildScheduleGroups(schedule);

	it('drops emptied nominations and blocks while keeping node keys stable', () => {
		const filtered = schedule.filter((e) => e.id === '1');

		const result = filterScheduleGroups(allNodes, filtered);

		expect(summarize(result)).toEqual([
			{
				kind: 'block',
				title: 'Блок A',
				eventCount: 1,
				nominations: [{ title: 'Ном 1', eventIds: ['1'] }]
			}
		]);
		// The surviving block reuses its pre-filter key so Svelte keeps its rows.
		expect(result.map((node) => node.key)).toEqual(
			allNodes.filter((node) => node.kind === 'block' && node.title === 'Блок A').map((n) => n.key)
		);
	});

	it('keeps an interlude only when its event survives the filter', () => {
		const withBreak = filterScheduleGroups(
			allNodes,
			schedule.filter((e) => e.id === 'break')
		);
		expect(summarize(withBreak)).toEqual([{ kind: 'interlude', eventId: 'break' }]);

		const withoutBreak = filterScheduleGroups(
			allNodes,
			schedule.filter((e) => e.id === '1')
		);
		expect(withoutBreak.some((node) => node.kind === 'interlude')).toBe(false);
	});

	it('returns every node unchanged when nothing is filtered out', () => {
		expect(summarize(filterScheduleGroups(allNodes, schedule))).toEqual(summarize(allNodes));
	});

	it('returns no nodes when everything is filtered out', () => {
		expect(filterScheduleGroups(allNodes, [])).toEqual([]);
	});
});
