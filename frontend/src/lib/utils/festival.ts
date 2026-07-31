import type { ScheduleEventFullDTO } from '$lib/types/schedule';

import { FESTIVAL_START } from '$lib/constants/festival';

/**
 * Which stage of the festival the app is in. The home page renders a different
 * layout for each: a countdown and setup steps before, the running order during,
 * a wrap-up after.
 */
export type FestivalPhase = 'before' | 'live' | 'after';

/** Only the fields the phase depends on, so tests don't build whole events. */
type PhaseEvent = Pick<ScheduleEventFullDTO, 'actual_start_time' | 'is_current' | 'is_skipped'>;

/**
 * Work out the festival phase from the schedule, falling back to the clock.
 *
 * The schedule is the better signal because it reflects what actually happened
 * on stage: a programme that starts late, overruns or is cancelled outright
 * moves these flags, while `FESTIVAL_START` stays where it was written months
 * earlier. The clock only decides the run-up, when no act has been run yet and
 * there is nothing else to go on.
 */
export function resolveFestivalPhase(schedule: PhaseEvent[], now: number): FestivalPhase {
	// A skipped act never runs, so it must not hold the phase back from 'after'.
	const running = schedule.filter((event) => !event.is_skipped);

	// An act marked as current is the organizers saying "we are on stage now" —
	// the strongest signal available, so it wins over everything below.
	if (running.some((event) => event.is_current)) {
		return 'live';
	}

	const started = running.filter((event) => event.actual_start_time !== null);

	// Nothing has run yet: either the festival hasn't started, or it has and the
	// organizers just haven't marked the first act. An empty schedule (not
	// imported yet) lands here too.
	if (started.length === 0) {
		return now < FESTIVAL_START ? 'before' : 'live';
	}

	// Every act has had its turn and none is on stage — the programme is over.
	if (started.length === running.length) {
		return 'after';
	}

	return 'live';
}
