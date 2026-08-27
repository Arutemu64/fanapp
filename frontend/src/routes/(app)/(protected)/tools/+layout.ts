import { isReachable } from '$lib/services/reachability';
import { isOrg } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent }) => {
	const { user } = await parent();

	// The toolbox is org-only for now: the dashboard lists every tool an org may
	// hold and marks the ones they lack as locked, so an org with no tool
	// permissions still sees the section. Each page enforces its own permission.
	if (!isOrg(user)) {
		error(403, 'У тебя нет доступа к этому разделу');
	}

	// Every tool is an online-only mutation surface (import, broadcast, settings,
	// sync…) with nothing to read offline. Gate the whole subtree in one place —
	// +layout.svelte shows an online-only state — rather than per tool page.
	return { offlineUnavailable: !isReachable() };
};
