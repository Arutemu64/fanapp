import type { ScheduleEventWithSubscription } from '$lib/types/schedule';

const UP_NEXT_COUNT = 3;

export interface FeaturedAct {
	event: ScheduleEventWithSubscription;
	/** On stage now; false for the opening act before organizers mark the first one. */
	live: boolean;
}

export interface StageSnapshot {
	/** The act the hero shows: the one on stage, or the opening act before it starts. */
	featured: FeaturedAct | null;
	/** The next few acts after the featured one, skipped ones left out. */
	upNext: ScheduleEventWithSubscription[];
	/** The viewer's nearest subscribed act beyond `upNext`, which already shows its own. */
	nextSubscribed: ScheduleEventWithSubscription | null;
	/** The act on stage, for queue distances; null before the first one is marked. */
	current: ScheduleEventWithSubscription | null;
}

export function getStageSnapshot(schedule: ScheduleEventWithSubscription[]): StageSnapshot {
	const ordered = [...schedule].sort((a, b) => a.order - b.order);
	const currentIndex = ordered.findIndex((event) => event.is_current);
	const current = ordered[currentIndex] ?? null;

	// With nothing on stage yet, the whole programme is still ahead.
	const upcoming = ordered.slice(currentIndex + 1).filter((event) => !event.is_skipped);

	let featured: FeaturedAct | null = null;
	let afterFeatured = upcoming;
	if (current) {
		featured = { event: current, live: true };
	} else if (upcoming[0]) {
		featured = { event: upcoming[0], live: false };
		afterFeatured = upcoming.slice(1);
	}

	const upNext = afterFeatured.slice(0, UP_NEXT_COUNT);
	const later = afterFeatured.slice(UP_NEXT_COUNT);
	const nextSubscribed = later.find((event) => event.user_subscription !== null) ?? null;

	return { featured, upNext, nextSubscribed, current };
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
