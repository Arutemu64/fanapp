import RotateCcwClock from '@lucide/svelte/icons/rotate-ccw-clock';

import type { NavbarAction } from '#lib/types/navigation.js';

import { getScheduleOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { m } from '#lib/paraglide/messages.js';
import { canManageSchedule } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient } = await parent();
	void queryClient.query(getScheduleOptions()).catch(() => {});

	const actions = [
		{
			href: 'schedule/changes',
			label: m.schedule_changes_title(),
			icon: RotateCcwClock,
			visibleFor: canManageSchedule
		}
	] satisfies NavbarAction[];

	return { title: m.nav_schedule(), actions };
};
