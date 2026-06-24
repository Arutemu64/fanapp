import type { components } from '$lib/api/v1';

export type ScheduleItemFullDTO = components['schemas']['ScheduleItemFullDTO'];
export type SubscriptionFullDTO = components['schemas']['SubscriptionFullDTO'];
export type ScheduleChangeType = components['schemas']['ScheduleChangeType'];
export type ScheduleChangeFullDTO = components['schemas']['ScheduleChangeFullDTO'];
export type ScheduleChangeScheduleItemDTO = components['schemas']['ScheduleChangeScheduleItemDTO'];

/** The viewer's subscription to a single schedule item (id + reminder threshold). */
export type ItemSubscription = { id: string; counter: number };

/**
 * Schedule row as the page renders it: the universal schedule item plus the
 * viewer's own subscription. The schedule and subscriptions arrive from two
 * separate endpoints (so each caches independently) and are merged client-side
 * by schedule item id, reproducing the embedded `user_subscription` the
 * components expect.
 */
export type ScheduleItemWithSubscription = ScheduleItemFullDTO & {
	user_subscription: ItemSubscription | null;
};
