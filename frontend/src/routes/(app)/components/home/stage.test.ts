import { describe, expect, it } from 'vitest';

import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

import { actsUntil, getStageSnapshot } from './stage';

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

const SUBSCRIPTION = { id: 'sub', counter: 3 };

function ids(events: ScheduleEventWithSubscription[]): string[] {
	return events.map((item) => item.id);
}

describe('getStageSnapshot', () => {
	it('lists the acts after the current one, in programme order', () => {
		const schedule = [
			event({ id: 'c', order: 3 }),
			event({ id: 'a', order: 1 }),
			event({ id: 'b', order: 2, is_current: true }),
			event({ id: 'd', order: 4 })
		];

		const snapshot = getStageSnapshot(schedule);

		expect(snapshot.featured).toEqual({ event: schedule[2], live: true });
		expect(snapshot.current?.id).toBe('b');
		expect(ids(snapshot.upNext)).toEqual(['c', 'd']);
	});

	it('features the opening act, not live, before the first act is marked', () => {
		const schedule = [
			event({ id: 'skipped', order: 0, is_skipped: true }),
			event({ id: 'a', order: 1 }),
			event({ id: 'b', order: 2 })
		];

		const snapshot = getStageSnapshot(schedule);

		expect(snapshot.current).toBeNull();
		expect(snapshot.featured?.event.id).toBe('a');
		expect(snapshot.featured?.live).toBe(false);
		expect(ids(snapshot.upNext)).toEqual(['b']);
	});

	it('features nothing when the programme is empty', () => {
		expect(getStageSnapshot([]).featured).toBeNull();
	});

	it('leaves skipped acts out and caps the list at three', () => {
		const schedule = [
			event({ id: 'now', order: 0, is_current: true }),
			event({ id: 'a', order: 1 }),
			event({ id: 'skipped', order: 2, is_skipped: true }),
			event({ id: 'b', order: 3 }),
			event({ id: 'c', order: 4 }),
			event({ id: 'd', order: 5 })
		];

		expect(ids(getStageSnapshot(schedule).upNext)).toEqual(['a', 'b', 'c']);
	});

	it('finds the nearest subscribed act beyond the up-next list', () => {
		const schedule = [
			event({ id: 'now', order: 0, is_current: true }),
			event({ id: 'a', order: 1, user_subscription: SUBSCRIPTION }),
			event({ id: 'b', order: 2 }),
			event({ id: 'c', order: 3 }),
			event({ id: 'd', order: 4 }),
			event({ id: 'mine', order: 5, user_subscription: SUBSCRIPTION }),
			event({ id: 'later', order: 6, user_subscription: SUBSCRIPTION })
		];

		expect(getStageSnapshot(schedule).nextSubscribed?.id).toBe('mine');
	});

	it('has nothing up next once the last act is on stage', () => {
		const schedule = [event({ id: 'a', order: 1 }), event({ id: 'b', order: 2, is_current: true })];

		const snapshot = getStageSnapshot(schedule);

		expect(snapshot.upNext).toEqual([]);
		expect(snapshot.nextSubscribed).toBeNull();
	});
});

describe('actsUntil', () => {
	const current = event({ id: 'now', queue: 4 });

	it('counts queue positions between the act and the one on stage', () => {
		expect(actsUntil(event({ id: 'a', queue: 7 }), current)).toBe(3);
	});

	it('is null without a current act or a queue position', () => {
		expect(actsUntil(event({ id: 'a', queue: 7 }), null)).toBeNull();
		expect(actsUntil(event({ id: 'break', queue: null }), current)).toBeNull();
	});

	it('is null for an act that is not ahead', () => {
		expect(actsUntil(event({ id: 'a', queue: 4 }), current)).toBeNull();
	});
});
