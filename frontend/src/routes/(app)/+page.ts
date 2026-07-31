import { createApiClient } from '$lib/api';
import { loadSchedule, loadSubscriptions, mergeSubscriptions } from '$lib/api/schedule';
import { isReachable } from '$lib/services/reachability';
import { resolveFestivalPhase } from '$lib/utils/festival';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';

import type { PageLoad } from './$types';

type ApiClient = ReturnType<typeof createApiClient>;

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	depends('app:schedule');

	const { user } = await parent();
	const client = createApiClient();

	const [scheduleResult, subscriptions, canVote] = await Promise.all([
		loadSchedule(client, fetch),
		loadSubscriptions(client, fetch, user?.id),
		loadCanVote(client, fetch, Boolean(user))
	]);

	// This page is the PWA `start_url`, so it must render something on every boot —
	// including offline with an empty cache. A missing schedule degrades to the
	// clock-driven phase (countdown or wrap-up) rather than an error screen.
	const schedule = scheduleResult.data ?? [];

	// Resolved here rather than in the component so the phase and the navbar title
	// come from one value — and so re-running the load is the only thing that can
	// change either, which is what the `schedule_updated` stream triggers.
	const phase = resolveFestivalPhase(schedule, Date.now());

	return {
		// Before the festival the hero carries the page <h1>, so the navbar leaves the
		// slot empty; in the other phases nothing else does, so the navbar takes it.
		title: phase === 'before' ? undefined : 'ФАН ФАН',
		phase,
		schedule: mergeSubscriptions(schedule, subscriptions),
		canVote,
		stale: scheduleResult.stale,
		cachedAt: scheduleResult.cachedAt,
		offlineMiss: scheduleResult.data === undefined
	};
};

/**
 * Whether the viewer can vote right now, used to decide if the home page shows
 * the voting call to action. Guests never can, so their answer is known without
 * asking — one request saved on the launch screen. Votes are online-only, so
 * there is nothing to cache: an unreachable backend or an error simply hides the
 * call to action instead of promising a vote that would fail.
 */
async function loadCanVote(
	client: ApiClient,
	fetch: typeof globalThis.fetch,
	isAuthenticated: boolean
): Promise<boolean> {
	if (!isAuthenticated || !isReachable()) return false;

	try {
		const { data } = await client.GET('/voting/status', {
			fetch,
			signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
		});
		return data?.can_vote ?? false;
	} catch {
		return false;
	}
}
