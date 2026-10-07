import type { ScheduleEventFullDto, SubscriptionFullDto } from '$lib/api/generated';
import type { ScheduleEventWithSubscription } from '$lib/types/schedule';

import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { getSchedule, getSubscriptions } from '$lib/api/generated';
import { REQUIRED_READ_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';

/**
 * Load the schedule merged with the viewer's subscriptions. Read by the schedule
 * page and the home "now on stage" card, so both share one row shape. Throws a
 * SvelteKit error when either read fails: without the subscriptions every event
 * would show as unsubscribed, offering a subscribe the backend then rejects.
 */
export async function loadScheduleWithSubscriptions(
	fetch: typeof globalThis.fetch,
	userId: string | undefined
): Promise<ScheduleEventWithSubscription[]> {
	const client = createApiClient();

	// Schedule and subscriptions come from two endpoints. Fetch them concurrently —
	// total latency is the slower of the two, not the sum. Guests skip the
	// subscriptions request entirely.
	const [schedule, subscriptions] = await Promise.all([
		fetchSchedule(client, fetch),
		fetchSubscriptions(client, fetch, userId)
	]);

	return mergeSubscriptions(schedule, subscriptions);
}

async function fetchSchedule(
	client: ReturnType<typeof createApiClient>,
	fetch: typeof globalThis.fetch
): Promise<ScheduleEventFullDto[]> {
	const { data, error, response } = await getSchedule({
		client,
		fetch,
		signal: timeoutSignal(REQUIRED_READ_TIMEOUT_MS)
	});
	if (error || !data) {
		throwApiError(error, response, 'Не удалось загрузить программу');
	}
	return data.schedule ?? [];
}

/** Guests have no subscriptions, so their request is skipped. */
async function fetchSubscriptions(
	client: ReturnType<typeof createApiClient>,
	fetch: typeof globalThis.fetch,
	userId: string | undefined
): Promise<SubscriptionFullDto[]> {
	if (!userId) return [];

	const { data, error, response } = await getSubscriptions({
		client,
		fetch,
		signal: timeoutSignal(REQUIRED_READ_TIMEOUT_MS)
	});
	if (error || !data) {
		throwApiError(error, response, 'Не удалось загрузить подписки');
	}
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
