import {
	canGenerateTickets,
	canImportSchedule,
	canManageSettings,
	canRunSyncs,
	canSendNotifications
} from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent }) => {
	const { user } = await parent();

	// Gate the tools section by effective permissions, matching the backend's
	// per-permission checks. These are not role-bound: any staff member holding
	// one of these permissions may enter. Each page enforces its own too.
	const canSeeToolsSection =
		canManageSettings(user) ||
		canImportSchedule(user) ||
		canSendNotifications(user) ||
		canGenerateTickets(user) ||
		canRunSyncs(user);

	if (!canSeeToolsSection) {
		error(403, 'У тебя нет доступа к этому разделу');
	}
};
