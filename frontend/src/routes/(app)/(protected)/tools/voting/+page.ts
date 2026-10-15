import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { throwApiError } from '#lib/api/errors.js';
import { getVotingDashboardOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { queryForLoad } from '#lib/api/index.js';
import { m } from '#lib/paraglide/messages.js';
import { canManageVoting } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	// Mirror the backend voting:manage check before hitting the API, so the page
	// is not shown to users the endpoint would reject with a 403.
	if (!canManageVoting(user)) {
		error(403, m.voting_admin_forbidden());
	}

	// The voting-window form is seeded once from this, so it waits for a fresh
	// copy rather than a cached one an edit would then overwrite.
	const dashboard = await queryForLoad(queryClient, {
		...getVotingDashboardOptions(),
		staleTime: 0
	}).catch((apiError: unknown) =>
		throwApiError(apiError, undefined, m.voting_dashboard_load_failed())
	);

	return {
		title: m.nav_voting(),
		back: { href: 'tools', label: m.tools_back() } satisfies BackTarget,
		dashboard
	};
};
