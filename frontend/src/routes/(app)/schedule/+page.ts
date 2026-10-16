import { RotateCcwClock } from '@lucide/svelte';

import type { NavbarAction } from '#lib/types/navigation.js';

import { getScheduleOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { currentUserOptions } from '#lib/api/index.js';
import { m } from '#lib/paraglide/messages.js';
import { canManageSchedule } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient } = await parent();
	// Start the fetch as early as SvelteKit preloads the route (on hover/tap); the
	// page subscribes to the same query and renders the cached copy meanwhile.
	void queryClient.query(getScheduleOptions()).catch(() => {});

	// The operator's change log lives with the schedule it tracks, not in the tools
	// section, so it is one tap from here. Gated by the same permission the changes
	// page enforces.
	const user = queryClient.getQueryData(currentUserOptions().queryKey) ?? null;
	const actions: NavbarAction[] = [];
	if (canManageSchedule(user)) {
		actions.push({
			href: 'schedule/changes',
			label: m.schedule_changes_title(),
			icon: RotateCcwClock
		});
	}

	return { title: m.nav_schedule(), actions };
};
