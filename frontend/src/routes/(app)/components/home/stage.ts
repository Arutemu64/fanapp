import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

import { secondsUntilActs } from '#lib/utils/scheduleData.js';

const UP_NEXT_COUNT = 3;

export interface FeaturedAct {
	event: ScheduleEventWithSubscription;
	live: boolean;
}

export interface StageSnapshot {
	featured: FeaturedAct | null;
	upNext: ScheduleEventWithSubscription[];
	nextSubscribed: ScheduleEventWithSubscription | null;
	current: ScheduleEventWithSubscription | null;
	secondsAhead: Map<string, number>;
}

export function getStageSnapshot(
	schedule: ScheduleEventWithSubscription[],
	changeoverSeconds: number
): StageSnapshot {
	const ordered = [...schedule].sort((a, b) => a.order - b.order);
	const currentIndex = ordered.findIndex((event) => event.is_current);
	const current = ordered[currentIndex] ?? null;

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

	return {
		featured,
		upNext,
		nextSubscribed,
		current,
		secondsAhead: secondsUntilActs(schedule, changeoverSeconds)
	};
}

export function actsUntil(
	event: ScheduleEventWithSubscription,
	current: ScheduleEventWithSubscription | null
): number | null {
	if (current === null || event.position === null || current.position === null) return null;
	const distance = event.position - current.position;
	return distance > 0 ? distance : null;
}
