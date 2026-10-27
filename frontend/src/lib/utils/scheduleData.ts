import type {
	ScheduleDto,
	ScheduleEntryDto,
	SubscriptionFullDto
} from '#lib/api/generated/index.js';
import type {
	EventSubscription,
	ScheduleEntryWithSubscription,
	ScheduleEventWithSubscription
} from '#lib/types/schedule.js';

export interface QueuedSubscriptionChanges {
	subscribing: readonly { event_id: string; lead_minutes: number }[];
	unsubscribing: readonly string[];
}

const NO_QUEUED_CHANGES: QueuedSubscriptionChanges = { subscribing: [], unsubscribing: [] };

export const EMPTY_SCHEDULE: ScheduleDto = { current_event_id: null, entries: [] };

export function mergeSubscriptions(
	schedule: ScheduleDto,
	subscriptions: SubscriptionFullDto[],
	queued: QueuedSubscriptionChanges = NO_QUEUED_CHANGES
): ScheduleEntryWithSubscription[] {
	const leaving = new Set(queued.unsubscribing);
	const byEventId = new Map<string, EventSubscription>();
	for (const sub of subscriptions) {
		if (leaving.has(sub.id)) continue;
		byEventId.set(sub.event.id, { id: sub.id, lead_minutes: sub.lead_minutes, queued: false });
	}
	for (const { event_id, lead_minutes } of queued.subscribing) {
		if (byEventId.has(event_id)) continue;
		byEventId.set(event_id, { id: null, lead_minutes, queued: true });
	}

	return schedule.entries.map((entry) => {
		if (entry.type === 'block_start') return entry;
		return {
			...entry,
			is_current: entry.id === schedule.current_event_id,
			user_subscription: byEventId.get(entry.id) ?? null
		};
	});
}

export function scheduleEvents(
	entries: ScheduleEntryWithSubscription[]
): ScheduleEventWithSubscription[] {
	return entries.filter((entry) => entry.type === 'event');
}

export function secondsUntilActs(
	schedule: ScheduleEventWithSubscription[],
	changeoverSeconds: number
): Map<string, number> {
	const ahead = new Map<string, number>();
	const running = schedule
		.filter((event) => event.position !== null)
		.sort((a, b) => (a.position ?? 0) - (b.position ?? 0));
	const currentIndex = running.findIndex((event) => event.is_current);
	if (currentIndex === -1) return ahead;

	let elapsed = 0;
	let planned = 0;
	for (const event of running.slice(currentIndex)) {
		if (!event.is_current && planned > 0) {
			ahead.set(event.id, elapsed);
		}
		elapsed += event.duration_seconds + changeoverSeconds;
		planned += event.duration_seconds;
	}
	return ahead;
}

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
