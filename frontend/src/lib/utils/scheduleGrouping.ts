// Groups a flat schedule into block → nomination sections for the schedule page's
// sticky-header layout, with block-less rows lifted out as standalone interludes.
// Kept as pure functions (not inline `$derived.by` in the page) so the keying and
// interlude contracts below are unit-testable and the page script stays about
// wiring, not list surgery.

import type { ScheduleEventWithSubscription } from '$lib/types/schedule';

export type ScheduleNominationGroup = {
	// Identity for the keyed {#each}. Assigned from the unfiltered schedule so
	// it survives filtering — see `filterScheduleGroups`.
	key: string;
	// null for a run of rows inside a block that carry no nomination (a pause
	// tagged with its block, say). The page renders no sub-header for those.
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

// A row with no block: a break, the opening or the closing. It renders as a
// standalone row between block sections rather than inside one.
export type ScheduleInterlude = {
	kind: 'interlude';
	key: string;
	event: ScheduleEventWithSubscription;
};

export type ScheduleNode = ScheduleBlockGroup | ScheduleInterlude;

/**
 * Group the *unfiltered* schedule into an ordered list of block sections and
 * interlude rows. Each node's key describes a fixed run of the programme, so
 * deriving keys from a filtered list instead (e.g. its index) would rename every
 * node that follows one a search empties out — and Svelte would tear down and
 * rebuild those blocks, and every EventCard inside them, on each keystroke rather
 * than reusing them. Callers keep this in a `$derived` off the schedule, so it
 * only recomputes when the schedule reloads.
 *
 * Grouping is keyed on block presence: a row with no block is an interlude and
 * never joins a block run, so a break between two same-block runs leaves them as
 * two sections (organizers keep a mid-block pause inside its block by giving it
 * that block with a blank nomination). A stray nomination on a block-less row is
 * ignored — there is no block for it to sit under.
 */
export function buildScheduleGroups(schedule: ScheduleEventWithSubscription[]): ScheduleNode[] {
	const nodes: ScheduleNode[] = [];

	for (const event of schedule) {
		const blockTitle = event.block_title?.trim() || null;

		if (blockTitle === null) {
			nodes.push({ kind: 'interlude', key: `interlude-${nodes.length}`, event });
			continue;
		}

		const nominationTitle = event.nomination_title?.trim() || null;

		const lastNode = nodes.at(-1);
		let blockGroup: ScheduleBlockGroup;
		if (lastNode?.kind === 'block' && lastNode.title === blockTitle) {
			blockGroup = lastNode;
		} else {
			blockGroup = {
				kind: 'block',
				key: `block-${nodes.length}`,
				title: blockTitle,
				eventCount: 0,
				nominations: []
			};
			nodes.push(blockGroup);
		}

		blockGroup.eventCount += 1;

		let nominationGroup = blockGroup.nominations.at(-1);
		if (!nominationGroup || nominationGroup.title !== nominationTitle) {
			nominationGroup = {
				key: `${blockGroup.key}-nomination-${blockGroup.nominations.length}`,
				title: nominationTitle,
				events: []
			};
			blockGroup.nominations.push(nominationGroup);
		}

		nominationGroup.events.push(event);
	}

	return nodes;
}

/**
 * The same node list as {@link buildScheduleGroups} with filtered-out events —
 * and any block section they emptied — removed. Nodes keep the keys they were
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
