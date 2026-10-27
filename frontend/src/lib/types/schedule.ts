import type { ScheduleBlockStartDto, ScheduleEventFullDto } from '#lib/api/generated/index.js';

export type EventSubscription =
	| { id: string; lead_minutes: number; queued: false }
	| { id: null; lead_minutes: number; queued: true };

export type ScheduleEventWithSubscription = ScheduleEventFullDto & {
	// Derived from the schedule's `current_event_id`.
	is_current: boolean;
	user_subscription: EventSubscription | null;
};

export type ScheduleEntryWithSubscription = ScheduleEventWithSubscription | ScheduleBlockStartDto;
