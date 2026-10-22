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

	// The event-role form is seeded once from this, so it waits for a fresh copy
	// rather than a cached one an edit would then overwrite.
	let eventRoles = null;
	if (hasPermission(user, 'tickets:generate')) {
		eventRoles = await queryForLoad(queryClient, {
			...getTcloudEventRolesOptions(),
			staleTime: 0
		}).catch((apiError: unknown) =>
			throwApiError(apiError, undefined, m.tcloud_roles_load_failed())
		);
	}

	return {
		title: m.tool_tickets(),
		back: { href: 'tools', label: m.tools_back() } satisfies BackTarget,
		eventRoles
	};
};
