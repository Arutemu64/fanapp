import { error } from '@sveltejs/kit';
import { canImportSchedule, canManageSettings, canSendNotifications } from '$lib/utils/permissions';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals }) => {
	// Gate the organizer section by effective permissions (ORG resolves via the
	// wildcard), matching the backend's per-permission checks. Each page below
	// still enforces its own specific permission.
	const user = locals.user;
	const canSeeOrganizerSection =
		canManageSettings(user) || canImportSchedule(user) || canSendNotifications(user);

	if (!canSeeOrganizerSection) {
		error(403, 'У тебя нет доступа к разделу организаторов');
	}
};
