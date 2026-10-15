import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { m } from '#lib/paraglide/messages.js';
import { canGenerateTickets } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	// Mirror the backend TICKETS_GENERATE check so the page is not shown to
	// users who would be rejected on submit.
	if (!canGenerateTickets(user)) {
		error(403, m.tickets_forbidden());
	}

	return {
		title: m.tool_generate_tickets(),
		back: { href: 'tools', label: m.tools_back() } satisfies BackTarget
	};
};
