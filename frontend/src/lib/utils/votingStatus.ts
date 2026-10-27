import type { GetVotingStatusOutput } from '#lib/api/generated/index.js';

export function isVotingWindowOpen(
	start: string | null | undefined,
	end: string | null | undefined,
	now: number
): boolean {
	if (!start || !end) return false;
	return new Date(start).getTime() <= now && now < new Date(end).getTime();
}

export function isVotingOpenNow(state: GetVotingStatusOutput | undefined, now: number): boolean {
	if (state === undefined || state.status === 'disabled') return false;
	return isVotingWindowOpen(state.voting_start, state.voting_end, now);
}

export function hasVotingEnded(end: string | null | undefined, now: number): boolean {
	if (!end) return false;
	return new Date(end).getTime() <= now;
}
