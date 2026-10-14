import type { ScheduleEntryDto, SubscriptionFullDto } from '#lib/api/generated/index.js';
import type {
	ScheduleEntryWithSubscription,
	ScheduleEventWithSubscription
} from '#lib/types/schedule.js';

/**
 * Attach each event's subscription (matched by event id) to reproduce the merged
 * row shape. The schedule and the viewer's subscriptions are separate queries —
 * one shared by everyone, one per account — merged by the schedule page and the
 * home "now on stage" card alike, so both render the same rows. Block starts
 * pass through untouched: nobody subscribes to a heading.
 */
export function mergeSubscriptions(
	schedule: ScheduleEntryDto[],
	subscriptions: SubscriptionFullDto[]
): ScheduleEntryWithSubscription[] {
	const byEventId = new Map(
		subscriptions.map((sub) => [sub.event.id, { id: sub.id, counter: sub.counter }])
	);

	return schedule.map((entry) => {
		if (entry.kind === 'block_start') return entry;
		return { ...entry, user_subscription: byEventId.get(entry.id) ?? null };
	});
}

/** The programme's events, in order, without the block starts between them. */
export function scheduleEvents(
	entries: ScheduleEntryWithSubscription[]
): ScheduleEventWithSubscription[] {
	return entries.filter((entry) => entry.kind === 'event');
}

/**
 * Each event's block title, for search: an event belongs to the nearest block
 * start above it, and events above the first block start belong to none.
 */
export function blockTitleByEventId(entries: ScheduleEntryDto[]): Map<string, string> {
	const titles = new Map<string, string>();
	let blockTitle: string | null = null;

	for (const entry of entries) {
		if (entry.kind === 'block_start') {
			blockTitle = entry.title;
		} else if (blockTitle !== null) {
			titles.set(entry.id, blockTitle);
		}
	}

	return titles;
}
