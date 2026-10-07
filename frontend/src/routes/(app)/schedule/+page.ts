import type { NavbarAction } from '$lib/types/navigation';

import { canManageSchedule } from '$lib/utils/permissions';
import { loadScheduleWithSubscriptions } from '$lib/utils/scheduleData';
import { History } from '@lucide/svelte';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends, parent }) => {
	depends('app:schedule');

	const { user } = await parent();
	const schedule = await loadScheduleWithSubscriptions(fetch, user?.id);

	// The operator's change log lives with the schedule it tracks, not in the tools
	// section, so it is one tap from here. Gated by the same permission the changes
	// page enforces.
	const actions: NavbarAction[] = [];
	if (canManageSchedule(user)) {
		actions.push({ href: '/schedule/changes', label: 'Изменения программы', icon: History });
	}

	return {
		title: 'Программа',
		actions,
		schedule
	};
};
