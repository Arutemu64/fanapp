import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { getSyncSourcesOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { canRunSync } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	// Mirror the backend SYNC_RUN check so the page is not shown to users who
	// would be rejected on submit.
	if (!canRunSync(user)) {
		error(403, 'У тебя нет доступа к синхронизации');
	}

	// Start the fetch as early as SvelteKit preloads the route (on hover/tap); the
	// page subscribes to the same query.
	void queryClient.query(getSyncSourcesOptions()).catch(() => {});

	return {
		title: 'Синхронизация',
		back: { href: 'tools', label: 'Назад к инструментам' } satisfies BackTarget
	};
};
