import { resolve } from '$app/paths';
import { error, redirect } from '@sveltejs/kit';

import { getPublicConfigOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { queryForLoad } from '#lib/api/index.js';
import { OFFLINE_TOOL_HREFS } from '#lib/data/tools.js';
import { m } from '#lib/paraglide/messages.js';
import { isReachable } from '#lib/services/reachability.js';
import { resolvePath } from '#lib/utils/paths.js';
import { isStaff } from '#lib/utils/permissions.js';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent, url }) => {
	const { queryClient, user } = await parent();

	if (!isStaff(user)) {
		error(403, m.tools_forbidden());
	}

	const offline = !isReachable();
	const worksOffline = OFFLINE_TOOL_HREFS.some((href) => url.pathname === resolvePath(href));
	if (offline && !worksOffline && url.pathname !== resolve('tools')) {
		redirect(307, resolve('tools'));
	}

	const toolConfig = await queryForLoad(queryClient, {
		...getPublicConfigOptions(),
		staleTime: 'static'
	}).catch(() => ({ quest_enabled: true }));

	return { offlineUnavailable: offline, toolConfig };
};
