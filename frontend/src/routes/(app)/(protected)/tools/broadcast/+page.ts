import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { m } from '#lib/paraglide/messages.js';
import { canSendNotifications } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	// Mirror the backend NOTIFICATIONS_SEND check so the page is not shown to
	// users who would be rejected on submit.
	if (!canSendNotifications(user)) {
		error(403, m.broadcast_forbidden());
	}

	return {
		title: m.tool_broadcast_title(),
		back: { href: 'tools', label: m.tools_back() } satisfies BackTarget
	};
};
