import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { m } from '#lib/paraglide/messages.js';
import { canReadFeedback } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	// The tools layout already gates the section to organizers; mirror the backend
	// FEEDBACK_READ check here so a user without the grant isn't shown a page the
	// list request would reject.
	if (!canReadFeedback(user)) {
		error(403, m.tool_feedback_forbidden());
	}

	return {
		title: m.tool_feedback(),
		back: { href: 'tools', label: m.tools_back() } satisfies BackTarget
	};
};
