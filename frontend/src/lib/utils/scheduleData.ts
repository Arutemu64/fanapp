import type { ScheduleEventFullDto, SubscriptionFullDto } from '$lib/api/generated';
import type { ScheduleEventWithSubscription } from '$lib/types/schedule';

import { createApiClient } from '$lib/api';
import { getSchedule, getSubscriptions } from '$lib/api/generated';

/**
 * Load the schedule merged with the viewer's subscriptions. Read by the schedule
 * page and the home "now on stage" card, so both share one row shape. Resolves to
 * `undefined` when the schedule itself can't be loaded.
 */
export async function loadScheduleWithSubscriptions(
	fetch: typeof globalThis.fetch,
	userId: string | undefined
): Promise<ScheduleEventWithSubscription[] | undefined> {
	const client = createApiClient();

	// Schedule and subscriptions come from two endpoints. Fetch them concurrently —
	// total latency is the slower of the two, not the sum. Guests skip the
	// subscriptions request entirely.
	const [scheduleResult, subscriptions] = await Promise.all([
		getSchedule({ client, fetch }),
		fetchSubscriptions(client, fetch, userId)
	]);

	const { data, error: fetchError } = scheduleResult;
	if (fetchError || !data) return undefined;

	return mergeSubscriptions(data.schedule ?? [], subscriptions);
}

/**
 * Load the current user's subscriptions. Guests have none, so we skip the request
 * and return an empty list. A failure degrades to "no badges" rather than failing
 * the page — the schedule itself decides whether the page can render.
 */
async function fetchSubscriptions(
	client: ReturnType<typeof createApiClient>,
	fetch: typeof globalThis.fetch,
	userId: string | undefined
): Promise<SubscriptionFullDto[]> {
	if (!userId) return [];

	const { data, error: fetchError } = await getSubscriptions({ client, fetch });
	if (fetchError || !data) return [];

	return data.subscriptions ?? [];
}

/** Attach each event's subscription (matched by event id) to reproduce the merged row shape. */
function mergeSubscriptions(
	schedule: ScheduleEventFullDto[],
	subscriptions: SubscriptionFullDto[]
): ScheduleEventWithSubscription[] {
	const byEventId = new Map(
		subscriptions.map((sub) => [sub.event.id, { id: sub.id, counter: sub.counter }])
	);

	return schedule.map((event) => ({
		...event,
		user_subscription: byEventId.get(event.id) ?? null
	}));
}
