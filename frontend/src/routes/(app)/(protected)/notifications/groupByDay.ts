import { eventDayKey, formatDayHeading } from '#lib/utils/formatters.js';

export interface DayGroup<T> {
	key: string;
	heading: string;
	items: T[];
}

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
