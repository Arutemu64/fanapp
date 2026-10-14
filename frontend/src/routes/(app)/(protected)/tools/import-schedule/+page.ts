import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { m } from '#lib/paraglide/messages.js';
import { canImportSchedule } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	// Mirror the backend SCHEDULE_IMPORT check so the page is not shown to users
	// who would be rejected on submit.
	if (!canImportSchedule(user)) {
		error(403, m.import_forbidden());
	}

	return {
		title: m.tool_import_title(),
		back: { href: 'tools', label: m.tools_back() } satisfies BackTarget
	};
};
