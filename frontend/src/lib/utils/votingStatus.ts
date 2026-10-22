import type { GetVotingStatusOutput } from '#lib/api/generated/index.js';

/**
 * Whether `now` falls inside the configured voting window, mirroring the backend's
 * [start, end) rule (`AppSettings.is_voting_open`). A missing bound means voting
 * isn't scheduled, so it is closed.
 */
export function isVotingWindowOpen(
	start: string | null | undefined,
	end: string | null | undefined,
	now: number
): boolean {
	if (!start || !end) return false;
	return new Date(start).getTime() <= now && now < new Date(end).getTime();
}

/**
 * Whether to tell the viewer that voting is open right now. The server's
 * `disabled` wins over the client clock, which may run ahead of the server's;
 * `no_ticket` and `not_authenticated` say nothing about the window, so for those
 * the clock decides.
 */
export function isVotingOpenNow(state: GetVotingStatusOutput | undefined, now: number): boolean {
	if (state === undefined || state.status === 'disabled') return false;
	return isVotingWindowOpen(state.voting_start, state.voting_end, now);
}

/** Whether the voting window has closed for good — a later reopening is an organizer edit. */
export function hasVotingEnded(end: string | null | undefined, now: number): boolean {
	if (!end) return false;
	return new Date(end).getTime() <= now;
}
