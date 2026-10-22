import { describe, expect, it } from 'vitest';

import type { ScheduleEntryDto, SubscriptionFullDto } from '#lib/api/generated/index.js';

import { mergeSubscriptions } from './scheduleData';

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
