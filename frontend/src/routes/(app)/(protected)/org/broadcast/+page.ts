import { error } from '@sveltejs/kit';
import { canSendNotifications } from '$lib/utils/permissions';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	// Mirror the backend NOTIFICATIONS_SEND check so the page is not shown to
	// users who would be rejected on submit.
	if (!canSendNotifications(user)) {
		error(403, 'У тебя нет доступа к рассылке уведомлений');
	}

	return {
		title: 'Рассылка уведомлений'
	};
};
