import type { BackTarget } from '#lib/types/navigation.js';

import { requireTool } from '#lib/data/tools.js';
import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { toolConfig, user } = await parent();

	requireTool('generate-tickets', user, toolConfig);

	return {
		title: m.tool_generate_tickets(),
		back: { href: 'tools', label: m.tools_back() } satisfies BackTarget
	};
};
