import { canImportSchedule, canManageSettings, canSendNotifications } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent }) => {
	const { user } = await parent();

	// Gate the organizer section by effective permissions, matching the
	// backend's per-permission checks. Each page enforces its own too.
	const canSeeOrganizerSection =
		canManageSettings(user) || canImportSchedule(user) || canSendNotifications(user);

	if (!canSeeOrganizerSection) {
		error(403, 'У тебя нет доступа к разделу организаторов');
	}
};
