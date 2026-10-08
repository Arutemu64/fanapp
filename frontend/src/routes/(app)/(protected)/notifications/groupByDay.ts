import { eventDayKey, formatDayHeading } from '#lib/utils/formatters.js';

export interface DayGroup<T> {
	key: string;
	heading: string;
	items: T[];
}

/**
 * Split a newest-first feed into venue-clock day sections ("Сегодня", "Вчера",
 * "8 октября"), keeping the feed's order inside and across sections.
 *
 * Keyed by day rather than by run: the feed is merged from live SSE arrivals and
 * fetched pages, so one day can in principle show up twice in sequence, and a
 * repeated section key would break the keyed `{#each}` that renders them.
 */
export function groupByDay<T extends { created_at: string }>(
	items: ReadonlyArray<T>,
	now: number = Date.now()
): DayGroup<T>[] {
	const groups = new Map<string, DayGroup<T>>();

	for (const item of items) {
		const key = eventDayKey(item.created_at);
		const group = groups.get(key);

		if (group) {
			group.items.push(item);
		} else {
			groups.set(key, { key, heading: formatDayHeading(item.created_at, now), items: [item] });
		}
	}

	return [...groups.values()];
}
