import { describe, expect, it } from 'vitest';

import type { ScheduleEntryDto, SubscriptionFullDto } from '#lib/api/generated/index.js';
import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

import { mergeSubscriptions, secondsUntilActs } from './scheduleData';

const schedule = [
	{
		type: 'event',
		id: 'a',
		number: null,
		title: 'A',
		duration: 300,
		order: 1,
		is_current: false,
		is_skipped: false,
		nomination_title: null,
		position: null
	},
	{
		type: 'event',
		id: 'b',
		number: null,
		title: 'B',
		duration: 300,
		order: 2,
		is_current: false,
		is_skipped: false,
		nomination_title: null,
		position: null
	}
] as ScheduleEntryDto[];

const subscriptionToA = {
	id: 'sub-a',
	user_id: 'me',
	lead_minutes: 10,
	event: { id: 'a' }
} as SubscriptionFullDto;

function subscriptionOf(entries: ReturnType<typeof mergeSubscriptions>, id: string) {
	const entry = entries.find((candidate) => candidate.id === id);
	return entry?.type === 'event' ? entry.user_subscription : undefined;
}

describe('mergeSubscriptions', () => {
	it("attaches the server's subscriptions by event", () => {
		const merged = mergeSubscriptions(schedule, [subscriptionToA]);

		expect(subscriptionOf(merged, 'a')).toEqual({ id: 'sub-a', lead_minutes: 10, queued: false });
		expect(subscriptionOf(merged, 'b')).toBeNull();
	});

	it('shows a subscribe still in the queue, without an ID', () => {
		const merged = mergeSubscriptions(schedule, [], {
			subscribing: [{ event_id: 'b', lead_minutes: 25 }],
			unsubscribing: []
		});

		expect(subscriptionOf(merged, 'b')).toEqual({ id: null, lead_minutes: 25, queued: true });
	});

	it('hides a subscription whose unsubscribe is still in the queue', () => {
		const merged = mergeSubscriptions(schedule, [subscriptionToA], {
			subscribing: [],
			unsubscribing: ['sub-a']
		});

		expect(subscriptionOf(merged, 'a')).toBeNull();
	});

	it("prefers the server's copy once a queued subscribe has landed", () => {
		const merged = mergeSubscriptions(schedule, [subscriptionToA], {
			subscribing: [{ event_id: 'a', lead_minutes: 45 }],
			unsubscribing: []
		});

		expect(subscriptionOf(merged, 'a')).toEqual({ id: 'sub-a', lead_minutes: 10, queued: false });
	});
});

describe('secondsUntilActs', () => {
	function act(
		id: string,
		position: number | null,
		duration: number,
		isCurrent = false
	): ScheduleEventWithSubscription {
		return {
			type: 'event',
			id,
			number: null,
			title: id,
			duration,
			order: position ?? 0,
			is_current: isCurrent,
			is_skipped: position === null,
			nomination_title: null,
			position,
			user_subscription: null
		};
	}

	it('sums the planned durations from the act on stage, counted in full', () => {
		const ahead = secondsUntilActs([
			act('done', 1, 60),
			act('now', 2, 120, true),
			act('skipped', null, 999),
			act('next', 3, 180),
			act('later', 4, 60)
		]);

		expect([...ahead]).toEqual([
			['next', 120],
			['later', 300]
		]);
	});

	it('estimates nothing before the first act is marked current', () => {
		expect(secondsUntilActs([act('a', 1, 60), act('b', 2, 60)]).size).toBe(0);
	});
});
