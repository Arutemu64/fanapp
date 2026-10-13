import type { ScheduleEventFullDto, SubscriptionFullDto } from '#lib/api/generated/index.js';
import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

/**
 * Attach each event's subscription (matched by event id) to reproduce the merged
 * row shape. The schedule and the viewer's subscriptions are separate queries —
 * one shared by everyone, one per account — merged by the schedule page and the
 * home "now on stage" card alike, so both render the same rows.
 */
export function mergeSubscriptions(
	schedule: ScheduleEventFullDto[],
	subscriptions: SubscriptionFullDto[]
): ScheduleEventWithSubscription[] {
	const byEventId = new Map(
		subscriptions.map((sub) => [sub.event.id, { id: sub.id, counter: sub.counter }])
	);

	return schedule.map((event) => ({
		...event,
		user_subscription: byEventId.get(event.id) ?? null
	}));
}
