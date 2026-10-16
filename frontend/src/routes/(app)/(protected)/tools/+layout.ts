import { resolve } from '$app/paths';
import { error, redirect } from '@sveltejs/kit';

import { getPublicConfigOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { queryForLoad } from '#lib/api/index.js';
import { FALLBACK_CONFIG } from '#lib/constants/festival.js';
import { m } from '#lib/paraglide/messages.js';
import { isReachable } from '#lib/services/reachability.js';
import { isStaff } from '#lib/utils/permissions.js';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent, url }) => {
	const { queryClient, user } = await parent();

	// The toolbox is for staff, and the dashboard lists only the tools a user
	// holds. Each page enforces its own permission.
	if (!isStaff(user)) {
		error(403, m.tools_forbidden());
	}

	// Every tool is an online-only mutation surface (import, broadcast, settings,
	// sync…) with nothing to read offline. Offline, redirect any sub-tool to the
	// hub: each sub-page load does `await parent()` first, so this redirect aborts
	// it before it fires a doomed API request. The hub itself has a static load, so
	// it lands safely and +layout.svelte renders the shared online-only state there.
	const offline = !isReachable();
	if (offline && url.pathname !== resolve('tools')) {
		redirect(307, resolve('tools'));
	}

	// Read once for every tool guard below (the quest tool is off with the quest).
	// Cached after the first visit; a failed fetch falls back to the defaults.
	const toolConfig = await queryForLoad(queryClient, getPublicConfigOptions()).catch(
		() => FALLBACK_CONFIG
	);

	return { offlineUnavailable: offline, toolConfig };
};
