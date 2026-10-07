import type { ScheduleEventWithSubscription } from '$lib/types/schedule';

const UP_NEXT_COUNT = 3;

export interface StageSnapshot {
	/** The act on stage, or null before organizers mark the first one. */
	current: ScheduleEventWithSubscription | null;
	/** The next few acts still to come, skipped ones left out. */
	upNext: ScheduleEventWithSubscription[];
	/** The viewer's nearest subscribed act beyond `upNext`, which already shows its own. */
	nextSubscribed: ScheduleEventWithSubscription | null;
}

export function getStageSnapshot(schedule: ScheduleEventWithSubscription[]): StageSnapshot {
	const ordered = [...schedule].sort((a, b) => a.order - b.order);
	const currentIndex = ordered.findIndex((event) => event.is_current);
	const current = ordered[currentIndex] ?? null;

	// With nothing on stage yet, the whole programme is still ahead.
	const upcoming = ordered.slice(currentIndex + 1).filter((event) => !event.is_skipped);
	const upNext = upcoming.slice(0, UP_NEXT_COUNT);
	const later = upcoming.slice(UP_NEXT_COUNT);
	const nextSubscribed = later.find((event) => event.user_subscription !== null) ?? null;

	return { current, upNext, nextSubscribed };
}

/**
 * How many acts away `event` is from the one on stage, by queue position — the
 * same drift-proof distance the schedule rows show (ADR-0014). Null when either
 * has no queue position or the event isn't ahead.
 */
export function actsUntil(
	event: ScheduleEventWithSubscription,
	current: ScheduleEventWithSubscription | null
): number | null {
	if (current === null || event.queue === null || current.queue === null) return null;
	const distance = event.queue - current.queue;
	return distance > 0 ? distance : null;
}
