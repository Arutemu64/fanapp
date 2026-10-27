import type {
	ScheduleEntryWithSubscription,
	ScheduleEventWithSubscription
} from '#lib/types/schedule.js';

interface ScheduleNominationGroup {
	key: string;
	title: string | null;
	events: ScheduleEventWithSubscription[];
}

export interface ScheduleBlockGroup {
	kind: 'block';
	key: string;
	title: string;
	eventCount: number;
	nominations: ScheduleNominationGroup[];
}

interface ScheduleInterlude {
	kind: 'interlude';
	key: string;
	event: ScheduleEventWithSubscription;
}

export type ScheduleNode = ScheduleBlockGroup | ScheduleInterlude;

export function buildScheduleGroups(schedule: ScheduleEntryWithSubscription[]): ScheduleNode[] {
	const nodes: ScheduleNode[] = [];
	let blockGroup: ScheduleBlockGroup | null = null;

	for (const entry of schedule) {
		if (entry.type === 'block_start') {
			blockGroup = {
				kind: 'block',
				key: `block-${entry.id}`,
				title: entry.title,
				eventCount: 0,
				nominations: []
			};
			nodes.push(blockGroup);
			continue;
		}

		if (blockGroup === null) {
			nodes.push({ kind: 'interlude', key: `interlude-${entry.id}`, event: entry });
			continue;
		}

		blockGroup.eventCount += 1;

		const nominationTitle = entry.nomination_title?.trim() || null;
		let nominationGroup = blockGroup.nominations.at(-1);
		if (nominationGroup?.title !== nominationTitle) {
			nominationGroup = {
				key: `${blockGroup.key}-nomination-${blockGroup.nominations.length}`,
				title: nominationTitle,
				events: []
			};
			blockGroup.nominations.push(nominationGroup);
		}

		nominationGroup.events.push(entry);
	}

	return nodes;
}

export function filterScheduleGroups(
	allNodes: ScheduleNode[],
	filtered: ScheduleEventWithSubscription[]
): ScheduleNode[] {
	const visibleEventIds = new Set(filtered.map((event) => event.id));
	const nodes: ScheduleNode[] = [];

	for (const node of allNodes) {
		if (node.kind === 'interlude') {
			if (visibleEventIds.has(node.event.id)) {
				nodes.push(node);
			}
			continue;
		}

		const nominations: ScheduleNominationGroup[] = [];
		let eventCount = 0;

		for (const nomination of node.nominations) {
			const events = nomination.events.filter((event) => visibleEventIds.has(event.id));
			if (events.length === 0) continue;

			nominations.push({ ...nomination, events });
			eventCount += events.length;
		}

		if (nominations.length > 0) {
			nodes.push({ ...node, eventCount, nominations });
		}
	}

	return nodes;
}
