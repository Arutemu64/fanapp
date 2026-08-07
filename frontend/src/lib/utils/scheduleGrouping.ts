// Groups a flat schedule into block → nomination sections for the schedule page's
// sticky-header layout. Kept as pure functions (not inline `$derived.by` in the
// page) so the two-stage keying contract below is unit-testable and the page
// script stays about wiring, not list surgery.

import type { ScheduleEventWithSubscription } from '$lib/types/schedule';

export type ScheduleNominationGroup = {
	// Identity for the keyed {#each}. Assigned from the unfiltered schedule so
	// it survives filtering — see `filterScheduleGroups`.
	key: string;
	title: string;
	events: ScheduleEventWithSubscription[];
};

export type ScheduleBlockGroup = {
	key: string;
	title: string;
	eventCount: number;
	nominations: ScheduleNominationGroup[];
};

/**
 * Group the *unfiltered* schedule into block/nomination sections. Each group's
 * key describes a fixed run of the programme, so deriving keys from a filtered
 * list instead (e.g. its index) would rename every group that follows one a
 * search empties out — and Svelte would tear down and rebuild those blocks, and
 * every EventCard inside them, on each keystroke rather than reusing them.
 * Callers keep this in a `$derived` off the schedule, so it only recomputes when
 * the schedule reloads.
 */
export function buildScheduleGroups(
	schedule: ScheduleEventWithSubscription[]
): ScheduleBlockGroup[] {
	const groups: ScheduleBlockGroup[] = [];

	for (const event of schedule) {
		const blockTitle = event.block_title?.trim() || 'Без блока';
		const nominationTitle = event.nomination_title?.trim() || 'Без номинации';

		let blockGroup = groups.at(-1);
		if (!blockGroup || blockGroup.title !== blockTitle) {
			blockGroup = {
				key: `block-${groups.length}`,
				title: blockTitle,
				eventCount: 0,
				nominations: []
			};
			groups.push(blockGroup);
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

	return groups;
}

/**
 * The same tree as {@link buildScheduleGroups} with filtered-out events — and
 * any group they emptied — removed. Groups keep the keys they were built with,
 * so a block that survives the filter keeps its identity and its rendered rows.
 * Takes pre-built groups (not the raw schedule) so a keystroke only re-runs this
 * cheap filter pass, never the full re-grouping above.
 */
export function filterScheduleGroups(
	allGroups: ScheduleBlockGroup[],
	filtered: ScheduleEventWithSubscription[]
): ScheduleBlockGroup[] {
	const visibleEventIds = new Set(filtered.map((event) => event.id));
	const groups: ScheduleBlockGroup[] = [];

	for (const block of allGroups) {
		const nominations: ScheduleNominationGroup[] = [];
		let eventCount = 0;

		for (const nomination of block.nominations) {
			const events = nomination.events.filter((event) => visibleEventIds.has(event.id));
			if (events.length === 0) continue;

			nominations.push({ ...nomination, events });
			eventCount += events.length;
		}

		if (nominations.length > 0) {
			groups.push({ ...block, eventCount, nominations });
		}
	}

	return groups;
}
