import { resolve } from '$app/paths';
import { isReachable } from '$lib/services/reachability';
import { isOrg } from '$lib/utils/permissions';
import { error, redirect } from '@sveltejs/kit';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent, url }) => {
	const { user } = await parent();

	// The toolbox is org-only for now: the dashboard lists every tool an org may
	// hold and marks the ones they lack as locked, so an org with no tool
	// permissions still sees the section. Each page enforces its own permission.
	if (!isOrg(user)) {
		error(403, 'У тебя нет доступа к этому разделу');
	}

	// Every tool is an online-only mutation surface (import, broadcast, settings,
	// sync…) with nothing to read offline. Offline, redirect any sub-tool to the
	// hub: each sub-page load does `await parent()` first, so this redirect aborts
	// it before it fires a doomed API request. The hub itself has a static load, so
	// it lands safely and +layout.svelte renders the shared online-only state there.
	const offline = !isReachable();
	if (offline && url.pathname !== resolve('/tools')) {
		redirect(307, resolve('/tools'));
	}

	return { offlineUnavailable: offline };
};
