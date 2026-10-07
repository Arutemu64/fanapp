import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { listUserNotifications } from '$lib/api/generated';
import {
	NOTIFICATION_PAGE_REQUEST_LIMIT,
	NOTIFICATION_PAGE_SIZE
} from '$lib/constants/notifications';
import { REQUIRED_READ_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends }) => {
	depends('app:notifications');

	const client = createApiClient();

	const {
		data,
		error: fetchError,
		response
	} = await listUserNotifications({
		client,
		fetch,
		signal: timeoutSignal(REQUIRED_READ_TIMEOUT_MS),
		query: {
			limit: NOTIFICATION_PAGE_REQUEST_LIMIT,
			offset: 0
		}
	});
	if (fetchError || !data) {
		throwApiError(fetchError, response, 'Не удалось загрузить уведомления');
	}

	const notifications = data.notifications ?? [];

	return {
		title: 'Уведомления',
		notifications: notifications.slice(0, NOTIFICATION_PAGE_SIZE),
		hasMore: notifications.length > NOTIFICATION_PAGE_SIZE
	};
};
