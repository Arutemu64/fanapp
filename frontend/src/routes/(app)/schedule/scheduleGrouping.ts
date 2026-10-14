// Groups a flat schedule into block → nomination sections for the schedule page's
// sticky-header layout, with the rows above the first block lifted out as
// standalone interludes.
// Kept as pure functions (not inline `$derived.by` in the page) so the keying and
// interlude contracts below are unit-testable and the page script stays about
// wiring, not list surgery.

import type {
	ScheduleEntryWithSubscription,
	ScheduleEventWithSubscription
} from '#lib/types/schedule.js';

type ScheduleNominationGroup = {
	// Identity for the keyed {#each}. Assigned from the unfiltered schedule so
	// it survives filtering — see `filterScheduleGroups`.
	key: string;
	// null for a run of rows inside a block that carry no nomination (a pause,
	// say). The page renders no sub-header for those.
	title: string | null;
	events: ScheduleEventWithSubscription[];
};

export type ScheduleBlockGroup = {
	kind: 'block';
	key: string;
	title: string;
	eventCount: number;
	nominations: ScheduleNominationGroup[];
};

// A row above the first block start, such as the opening. It belongs to no
// block, so it renders as a standalone row rather than inside a section.
type ScheduleInterlude = {
	kind: 'interlude';
	key: string;
	event: ScheduleEventWithSubscription;
};

export type ScheduleNode = ScheduleBlockGroup | ScheduleInterlude;

/**
 * Group the *unfiltered* schedule into an ordered list of block sections and
 * interlude rows. A block is a block start entry plus every event after it, up
 * to the next block start. Each node is keyed by the id of the entry that
 * opens it, so a node keeps its key while a search filters the list around it —
 * and Svelte reuses its rendered rows, and every EventCard inside them, on each
 * keystroke rather than rebuilding them. Callers keep this in a `$derived` off
 * the schedule, so it only recomputes when the schedule reloads.
 *
 * A stray nomination on an interlude is ignored — there is no block for it to
 * sit under.
 */
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
		if (!nominationGroup || nominationGroup.title !== nominationTitle) {
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

/**
 * The same node list as {@link buildScheduleGroups} with filtered-out events —
 * and any block section they emptied, or that never had any — removed. Nodes keep the keys they were
 * built with, so a block that survives the filter keeps its identity and its
 * rendered rows. Takes pre-built nodes (not the raw schedule) so a keystroke only
 * re-runs this cheap filter pass, never the full re-grouping above.
 */
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
