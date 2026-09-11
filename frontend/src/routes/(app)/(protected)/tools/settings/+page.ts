import { getSettingsOptions } from '$lib/api/client/@tanstack/svelte-query.gen';
import { throwHeyApiError } from '$lib/api/errors';
import { queryClient } from '$lib/api/queryClient';
import { canManageSettings } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

// Pilot migration to hey-api + TanStack Query — see
// docs/sketches/hey-api-tanstack-query-migration.md. This page is online-only
// (organizer tooling, no offline cache today), which is what makes it a
// low-risk first mover: no persister/offline-scope work needed to prove the
// generated-options + shared QueryClient + Russian error funnel loop end to end.
export const load: PageLoad = async ({ fetch, parent }) => {
	const { user } = await parent();

	// Mirror the backend SETTINGS_MANAGE check before hitting the API, so the
	// page is not shown to users who would be rejected.
	if (!canManageSettings(user)) {
		error(403, 'У тебя нет доступа к настройкам фестиваля');
	}

	// Blocks like the old `load` did, so the shared app-shell skeleton still
	// covers this page's first paint (docs/frontend.md §4). Prefetches into the
	// shared `queryClient` cache; the page's own `createQuery` reads the same
	// entry and gets background refetch after this.
	try {
		await queryClient.ensureQueryData(getSettingsOptions({ fetch }));
	} catch (apiError) {
		throwHeyApiError(apiError, 'Не удалось загрузить настройки фестиваля');
	}

	return {
		title: 'Настройки фестиваля'
	};
};
