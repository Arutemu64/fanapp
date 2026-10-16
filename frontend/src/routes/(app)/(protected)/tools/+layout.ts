import { resolve } from '$app/paths';
import { error, redirect } from '@sveltejs/kit';

import { m } from '#lib/paraglide/messages.js';
import { isReachable } from '#lib/services/reachability.js';
import { isStaff } from '#lib/utils/permissions.js';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent, url }) => {
	const { user } = await parent();

	// The toolbox is for staff. The dashboard shows an organizer every tool, the
	// ones they lack locked, and a volunteer only the tools they hold. Each page
	// enforces its own permission.
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

	return { offlineUnavailable: offline };
};
