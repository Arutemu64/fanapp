import type { PublicConfigDto } from '$lib/api/generated';
import type { ScheduleEventWithSubscription } from '$lib/types/schedule';

import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { getPublicConfig } from '$lib/api/generated';
import { REQUIRED_READ_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';
import { loadScheduleWithSubscriptions } from '$lib/utils/scheduleData';
import { fetchVotingStatus } from '$lib/utils/votingStatus';
import { isHttpError } from '@sveltejs/kit';

import type { PageLoad } from './$types';

// Public config drives the hero's phase (before/during/after) and countdown, so
// the page can't render without it.
async function loadConfig(fetch: typeof globalThis.fetch): Promise<PublicConfigDto> {
	const client = createApiClient();
	const { data, error, response } = await getPublicConfig({
		client,
		fetch,
		signal: timeoutSignal(REQUIRED_READ_TIMEOUT_MS)
	});
	if (error || !data) {
		throwApiError(error, response, 'Не удалось загрузить данные фестиваля');
	}
	return data;
}

// A schedule failure is not an error here: home just leaves out what needs it.
async function loadOptionalSchedule(
	fetch: typeof globalThis.fetch,
	userId: string | undefined
): Promise<ScheduleEventWithSubscription[]> {
	try {
		return await loadScheduleWithSubscriptions(fetch, userId);
	} catch (err) {
		if (isHttpError(err)) return [];
		throw err;
	}
}

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	// 'app:config' also covers the voting window, which organizers edit in settings.
	depends('app:config');
	depends('app:schedule');

	// Reading the user through parent() re-runs this load on login, logout and a
	// linked ticket, which is what changes the voting status and subscriptions.
	const { user } = await parent();

	const [config, schedule, votingStatus] = await Promise.all([
		loadConfig(fetch),
		loadOptionalSchedule(fetch, user?.id),
		// Optional here: a failure hides the voting card and nothing else.
		fetchVotingStatus(fetch)
	]);

	return {
		// AppNavbar renders this as the page <h1>; it matches the tab label, as on
		// every other tab.
		title: 'Главная',
		config,
		schedule,
		votingStatus
	};
};
