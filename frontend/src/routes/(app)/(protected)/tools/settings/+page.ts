import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { throwApiError } from '#lib/api/errors.js';
import { getSettingsOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { queryForLoad } from '#lib/api/index.js';
import { m } from '#lib/paraglide/messages.js';
import { canManageSettings } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	// Mirror the backend SETTINGS_MANAGE check before hitting the API, so the
	// page is not shown to users who would be rejected.
	if (!canManageSettings(user)) {
		error(403, m.settings_forbidden());
	}

	// The form is seeded once from this, so it waits for a fresh copy rather than
	// a cached one an edit would then overwrite.
	const settings = await queryForLoad(queryClient, { ...getSettingsOptions(), staleTime: 0 }).catch(
		(apiError: unknown) => throwApiError(apiError, undefined, m.settings_load_failed())
	);

	return {
		title: m.tool_settings(),
		back: { href: 'tools', label: m.tools_back() } satisfies BackTarget,
		settings
	};
};
