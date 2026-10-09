import type { GetVotingStateOutput } from '#lib/api/generated/index.js';

import { getVotingStatus } from '#lib/api/generated/index.js';
import { createApiClient } from '#lib/api/index.js';
import { isReachable, isUnreachableResponse } from '#lib/services/reachability.js';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '#lib/utils/fetchTimeout.js';

/**
 * Fetch the viewer's voting status, or `undefined` when it can't be had. Voting
 * status is a live, online-only read — a stale "open" would lead to a ballot that
 * can't be submitted — so it is never cached, and every caller treats `undefined`
 * as "show nothing about voting".
 */
export async function fetchVotingStatus(
	fetch: typeof globalThis.fetch
): Promise<GetVotingStateOutput | undefined> {
	// When the backend is known unreachable, skip the doomed request.
	if (!isReachable()) return undefined;

	const { data, error, response } = await getVotingStatus({
		client: createApiClient(),
		fetch,
		signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
	});

	if (error) {
		// Not reaching the backend is expected offline — hide voting UI quietly.
		if (!isUnreachableResponse(response)) {
			console.error('Error fetching voting status:', error);
		}
		return undefined;
	}

	return data;
}

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
export function isVotingOpenNow(state: GetVotingStateOutput | undefined, now: number): boolean {
	if (state === undefined || state.status === 'disabled') return false;
	return isVotingWindowOpen(state.voting_start, state.voting_end, now);
}

/** Whether the voting window has closed for good — a later reopening is an organizer edit. */
export function hasVotingEnded(end: string | null | undefined, now: number): boolean {
	if (!end) return false;
	return new Date(end).getTime() <= now;
}
