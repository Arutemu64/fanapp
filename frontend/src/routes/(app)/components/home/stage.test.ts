import { describe, expect, it } from 'vitest';

import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

import { actsUntil, getStageSnapshot } from './stage';

function event(
	overrides: Partial<ScheduleEventWithSubscription> & Pick<ScheduleEventWithSubscription, 'id'>
): ScheduleEventWithSubscription {
	return {
		type: 'event',
		number: null,
		title: 'Выступление',
		duration_seconds: 300,
		is_current: false,
		is_skipped: false,
		nomination_title: null,
		position: null,
		user_subscription: null,
		...overrides
	};
}

const SUBSCRIPTION = { id: 'sub', lead_minutes: 15, queued: false } as const;

function ids(events: ScheduleEventWithSubscription[]): string[] {
	return events.map((item) => item.id);
}

describe('getStageSnapshot', () => {
	it('lists the acts after the current one, in programme order', () => {
		const schedule = [
			event({ id: 'a', number: 3 }),
			event({ id: 'b', number: 1, is_current: true }),
			event({ id: 'c', number: 4 }),
			event({ id: 'd', number: 2 })
		];

		const snapshot = getStageSnapshot(schedule, 0);

		expect(snapshot.featured).toEqual({ event: schedule[1], live: true });
		expect(snapshot.current?.id).toBe('b');
		expect(ids(snapshot.upNext)).toEqual(['c', 'd']);
	});

	it('features the opening act, not live, before the first act is marked', () => {
		const schedule = [
			event({ id: 'skipped', is_skipped: true }),
			event({ id: 'a' }),
			event({ id: 'b' })
		];

		const snapshot = getStageSnapshot(schedule, 0);

		expect(snapshot.current).toBeNull();
		expect(snapshot.featured?.event.id).toBe('a');
		expect(snapshot.featured?.live).toBe(false);
		expect(ids(snapshot.upNext)).toEqual(['b']);
	});

	it('features nothing when the programme is empty', () => {
		expect(getStageSnapshot([], 0).featured).toBeNull();
	});

	it('leaves skipped acts out and caps the list at three', () => {
		const schedule = [
			event({ id: 'now', is_current: true }),
			event({ id: 'a' }),
			event({ id: 'skipped', is_skipped: true }),
			event({ id: 'b' }),
			event({ id: 'c' }),
			event({ id: 'd' })
		];

		expect(ids(getStageSnapshot(schedule, 0).upNext)).toEqual(['a', 'b', 'c']);
	});

	it('finds the nearest subscribed act beyond the up-next list', () => {
		const schedule = [
			event({ id: 'now', is_current: true }),
			event({ id: 'a', user_subscription: SUBSCRIPTION }),
			event({ id: 'b' }),
			event({ id: 'c' }),
			event({ id: 'd' }),
			event({ id: 'mine', user_subscription: SUBSCRIPTION }),
			event({ id: 'later', user_subscription: SUBSCRIPTION })
		];

		expect(getStageSnapshot(schedule, 0).nextSubscribed?.id).toBe('mine');
	});

	it('has nothing up next once the last act is on stage', () => {
		const schedule = [event({ id: 'a' }), event({ id: 'b', is_current: true })];

		const snapshot = getStageSnapshot(schedule, 0);

		expect(snapshot.upNext).toEqual([]);
		expect(snapshot.nextSubscribed).toBeNull();
	});
});

describe('actsUntil', () => {
	const current = event({ id: 'now', position: 4 });

	it('counts positions between the act and the one on stage', () => {
		expect(actsUntil(event({ id: 'a', position: 7 }), current)).toBe(3);
	});

	it('is null without a current act or a position', () => {
		expect(actsUntil(event({ id: 'a', position: 7 }), null)).toBeNull();
		expect(actsUntil(event({ id: 'break', position: null }), current)).toBeNull();
	});

	it('is null for an act that is not ahead', () => {
		expect(actsUntil(event({ id: 'a', position: 4 }), current)).toBeNull();
	});
});
