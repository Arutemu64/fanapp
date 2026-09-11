import type { MailingDto } from '$lib/api/client';

import { listBroadcasts } from '$lib/api/client';
import { BROADCAST_PAGE_REQUEST_LIMIT, BROADCAST_PAGE_SIZE } from '$lib/constants/notifications';
import { canSendNotifications } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	depends('app:broadcasts');

	const { user } = await parent();

	// Mirror the backend NOTIFICATIONS_SEND check so the page is not shown to
	// users who would be rejected on submit.
	if (!canSendNotifications(user)) {
		error(403, 'У тебя нет доступа к рассылке уведомлений');
	}

	// First page of the sent history. Best-effort: a failure must not block the
	// composer, so fall back to an empty list rather than erroring the page.
	let mailings: MailingDto[] = [];
	let hasMore = false;
	const { data } = await listBroadcasts({
		fetch,
		query: { limit: BROADCAST_PAGE_REQUEST_LIMIT, offset: 0 }
	});
	if (data) {
		mailings = data.mailings.slice(0, BROADCAST_PAGE_SIZE);
		hasMore = data.mailings.length > BROADCAST_PAGE_SIZE;
	}

	return {
		title: 'Рассылка уведомлений',
		mailings,
		hasMore
	};
};
