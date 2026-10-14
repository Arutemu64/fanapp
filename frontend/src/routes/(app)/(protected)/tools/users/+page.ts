import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { m } from '#lib/paraglide/messages.js';
import { canReadUsers } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	// The tools layout gates the section to organisers; mirror the backend
	// users:read check here so a user without the grant isn't shown a page the
	// list request would reject with a 403.
	if (!canReadUsers(user)) {
		error(403, m.users_forbidden());
	}

	return {
		title: m.tool_users_title(),
		back: { href: 'tools', label: m.tools_back() } satisfies BackTarget
	};
};
