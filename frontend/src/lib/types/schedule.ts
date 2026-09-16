import type { ScheduleEventFullDto } from '$lib/api/generated';

/** The viewer's subscription to a single event (id + reminder threshold). */
type EventSubscription = { id: string; counter: number };

/**
 * Schedule row as the page renders it: the universal event plus the viewer's
 * own subscription. The schedule and subscriptions arrive from two separate
 * endpoints (so each caches independently) and are merged client-side by event
 * id, reproducing the embedded `user_subscription` the components expect.
 */
export type ScheduleEventWithSubscription = ScheduleEventFullDto & {
	user_subscription: EventSubscription | null;
};
