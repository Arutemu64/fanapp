import type { BackTarget } from '#lib/types/navigation.js';

import { getSyncSourcesOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { requireTool } from '#lib/data/tools.js';
import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, toolConfig, user } = await parent();

	requireTool('sync', user, toolConfig);

	void queryClient.query(getSyncSourcesOptions()).catch(() => {});

	return {
		title: m.tool_sync(),
		back: { href: 'tools', label: m.tools_back() } satisfies BackTarget
	};
};
