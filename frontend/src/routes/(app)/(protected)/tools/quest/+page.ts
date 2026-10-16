import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { m } from '#lib/paraglide/messages.js';
import { canAwardQuest, canManageQuest } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	// Mirror the backend: quest:award gives points, quest:manage reviews and
	// cancels every award.
	if (!canAwardQuest(user) && !canManageQuest(user)) {
		error(403, m.tool_quest_forbidden());
	}

	return {
		title: m.tool_quest(),
		back: { href: 'tools', label: m.tools_back() } satisfies BackTarget
	};
};
