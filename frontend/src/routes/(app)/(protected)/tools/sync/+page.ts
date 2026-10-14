import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { getSyncSourcesOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { m } from '#lib/paraglide/messages.js';
import { canRunSync } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	// Mirror the backend SYNC_RUN check so the page is not shown to users who
	// would be rejected on submit.
	if (!canRunSync(user)) {
		error(403, m.sync_forbidden());
	}

	// Start the fetch as early as SvelteKit preloads the route (on hover/tap); the
	// page subscribes to the same query.
	void queryClient.query(getSyncSourcesOptions()).catch(() => {});

	return {
		title: m.tool_sync_title(),
		back: { href: 'tools', label: m.tools_back() } satisfies BackTarget
	};
};
