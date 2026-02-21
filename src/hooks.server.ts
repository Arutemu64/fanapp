import type { FullUserDTO } from '$lib/types/user';
import type { Handle } from '@sveltejs/kit';
import { api } from '$lib/api';

export const handle: Handle = async ({ event, resolve }) => {
	// Load current user - use event.fetch for server-side requests
	try {
		const user: FullUserDTO = await api.get('/users/me', { customFetch: event.fetch });
		event.locals.user = user;
	} catch {
		event.locals.user = null;
	}

	return resolve(event);
};
