import type { BackTarget } from '#lib/types/navigation.js';

import { throwApiError } from '#lib/api/errors.js';
import { getSettingsOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { queryForLoad } from '#lib/api/index.js';
import { requireTool } from '#lib/data/tools.js';
import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, toolConfig, user } = await parent();

	requireTool('settings', user, toolConfig);

	const settings = await queryForLoad(queryClient, { ...getSettingsOptions(), staleTime: 0 }).catch(
		(apiError: unknown) => throwApiError(apiError, m.settings_load_failed())
	);

	return {
		title: m.tool_settings(),
		back: { href: 'tools', label: m.tools_back() } satisfies BackTarget,
		settings
	};
};
