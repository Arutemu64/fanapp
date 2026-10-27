import type { BackTarget } from '#lib/types/navigation.js';

import { throwApiError } from '#lib/api/errors.js';
import {
	getSyncSourcesOptions,
	getTcloudEventRolesOptions
} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { queryForLoad } from '#lib/api/index.js';
import { requireTool } from '#lib/data/tools.js';
import { m } from '#lib/paraglide/messages.js';
import { hasPermission } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, toolConfig, user } = await parent();

	requireTool('tickets', user, toolConfig);

	if (hasPermission(user, 'sync:run')) {
		void queryClient.query(getSyncSourcesOptions()).catch(() => {});
	}

	let eventRoles = null;
	if (hasPermission(user, 'tickets:manage')) {
		eventRoles = await queryForLoad(queryClient, {
			...getTcloudEventRolesOptions(),
			staleTime: 0
		}).catch((apiError: unknown) => throwApiError(apiError, m.tcloud_roles_load_failed()));
	}

	return {
		title: m.tool_tickets(),
		back: { href: 'tools', label: m.tools_back() } satisfies BackTarget,
		eventRoles
	};
};
