import type { ScheduleEntryDto, SubscriptionFullDto } from '#lib/api/generated/index.js';
import type {
	EventSubscription,
	ScheduleEntryWithSubscription,
	ScheduleEventWithSubscription
} from '#lib/types/schedule.js';

/** Subscription writes still in the queue (ADR-0038), not yet in the server's list. */
export interface QueuedSubscriptionChanges {
	subscribing: ReadonlyArray<{ event_id: string; counter: number }>;
	/** Subscription IDs whose unsubscribe is waiting. */
	unsubscribing: ReadonlyArray<string>;
}

const NO_QUEUED_CHANGES: QueuedSubscriptionChanges = { subscribing: [], unsubscribing: [] };

/**
 * Attach each event's subscription (matched by event id) to reproduce the merged
 * row shape. The schedule and the viewer's subscriptions are separate queries —
 * one shared by everyone, one per account — merged by the schedule page and the
 * home "now on stage" card alike, so both render the same rows. Block starts
 * pass through untouched: nobody subscribes to a heading.
 *
 * Writes still waiting in the queue are laid over the server's list, so a
 * subscription made offline shows at once (marked `queued`) and one being
 * removed is already gone.
 */
export function mergeSubscriptions(
	schedule: ScheduleEntryDto[],
	subscriptions: SubscriptionFullDto[],
	queued: QueuedSubscriptionChanges = NO_QUEUED_CHANGES
): ScheduleEntryWithSubscription[] {
	const leaving = new Set(queued.unsubscribing);
	const byEventId = new Map<string, EventSubscription>();
	for (const sub of subscriptions) {
		if (leaving.has(sub.id)) continue;
		byEventId.set(sub.event.id, { id: sub.id, counter: sub.counter, queued: false });
	}
	for (const { event_id, counter } of queued.subscribing) {
		if (byEventId.has(event_id)) continue;
		byEventId.set(event_id, { id: null, counter, queued: true });
	}

	return schedule.map((entry) => {
		if (entry.type === 'block_start') return entry;
		return { ...entry, user_subscription: byEventId.get(entry.id) ?? null };
	});
}

/** The programme's events, in order, without the block starts between them. */
export function scheduleEvents(
	entries: ScheduleEntryWithSubscription[]
): ScheduleEventWithSubscription[] {
	return entries.filter((entry) => entry.type === 'event');
}

/**
 * Each event's block title, for search: an event belongs to the nearest block
 * start above it, and events above the first block start belong to none.
 */
export function blockTitleByEventId(entries: ScheduleEntryDto[]): Map<string, string> {
	const titles = new Map<string, string>();
	let blockTitle: string | null = null;

	for (const entry of entries) {
		if (entry.type === 'block_start') {
			blockTitle = entry.title;
		} else if (blockTitle !== null) {
			titles.set(entry.id, blockTitle);
		}
	}

	return titles;
}
