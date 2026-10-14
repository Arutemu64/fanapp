import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { m } from '#lib/paraglide/messages.js';
import { canManageSchedule } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

// Staff-only, so it lives in (protected): the URL stays /schedule/changes, and a
// session that expires while it is open hands it over to /login like any other
// members-only screen.
export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	if (!canManageSchedule(user)) {
		error(403, m.changes_forbidden());
	}

	return {
		title: m.schedule_changes_title(),
		back: { href: 'schedule', label: m.changes_back() } satisfies BackTarget
	};
};
