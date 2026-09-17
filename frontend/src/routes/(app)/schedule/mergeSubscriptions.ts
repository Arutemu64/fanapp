import type { ScheduleEventFullDto, SubscriptionFullDto } from '$lib/api/generated';
import type { ScheduleEventWithSubscription } from '$lib/types/schedule';

/**
 * Attach each event's subscription (matched by event id) to reproduce the merged
 * row shape the schedule components expect.
 *
 * The two halves come from separate endpoints so each caches on its own — the
 * programme is universal and survives logout, subscriptions are per-user and do
 * not.
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
