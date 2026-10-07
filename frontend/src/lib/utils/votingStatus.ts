import type { GetVotingStateOutput } from '$lib/api/generated';

import { createApiClient } from '$lib/api';
import { getVotingStatus } from '$lib/api/generated';
import { isBackendUnreachableStatus, isReachable, markReachable } from '$lib/services/reachability';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';

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

	const client = createApiClient();

	try {
		const { data, error, response } = await getVotingStatus({
			client,
			fetch,
			signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
		});

		if (error) {
			// The client returns a network failure (offline / timeout / abort) as an
			// error with no `response`, and a live proxy over a dead backend as a
			// gateway 5xx. Both mean unreachable: mark us so the page loads skip their
			// own doomed requests, and hide voting UI without a noisy console error.
			if (!response || isBackendUnreachableStatus(response.status)) {
				markReachable(false);
				return undefined;
			}
			console.error('Error fetching voting status:', error);
			return undefined;
		}

		return data;
	} catch {
		// Defensive: nothing above is expected to throw (the client resolves failures
		// into `error`), but an unexpected throw must not crash the caller's page.
		markReachable(false);
		return undefined;
	}
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

/** Whether the voting window has closed for good — a later reopening is an organizer edit. */
export function hasVotingEnded(end: string | null | undefined, now: number): boolean {
	if (!end) return false;
	return new Date(end).getTime() <= now;
}
