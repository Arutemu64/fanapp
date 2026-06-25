import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import {
	SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT,
	SCHEDULE_CHANGES_PAGE_SIZE
} from '$lib/constants/schedule_changes';
import { canManageSchedule } from '$lib/utils/permissions';
import { error, redirect } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	const { user } = await parent();

	if (!user) {
		redirect(303, '/login');
	}

	if (!canManageSchedule(user)) {
		error(403, 'У вас нет доступа к этой странице');
	}

	depends('app:schedule:changes');

	const client = createApiClient();

	// Staff-only operational feed: stale data would misrepresent live state, so
	// no offline cache here — fail hard when unreachable instead.
	// Over-fetch one item so the client can tell whether a next page exists.
	const {
		data,
		error: fetchError,
		response
	} = await client.GET('/schedule/changes/', {
		fetch,
		params: { query: { limit: SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT, offset: 0 } }
	});
	if (fetchError || !data) {
		throwApiError(fetchError, response, 'Не удалось загрузить изменения программы');
	}

	const changes = data.schedule_changes ?? [];
	return {
		title: 'Изменения программы',
		schedule_changes: changes.slice(0, SCHEDULE_CHANGES_PAGE_SIZE),
		hasMore: changes.length > SCHEDULE_CHANGES_PAGE_SIZE
	};
};
