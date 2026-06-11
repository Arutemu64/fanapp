import { error } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals }) => {
	// Block access to the entire organizer section if the user's role is not 'org'
	if (locals.user?.role !== 'org') {
		error(403, 'У тебя нет доступа к разделу организаторов');
	}
};
