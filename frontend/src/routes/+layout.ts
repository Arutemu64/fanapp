import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { getCurrentUser } from '$lib/api/generated';

import type { LayoutLoad } from './$types';

// SPA-only: render entirely on the client. There is no server render.
export const ssr = false;

export const load: LayoutLoad = async ({ fetch, depends }) => {
	depends('app:current-user');

	const client = createApiClient();
	const { data, response, error } = await getCurrentUser({ client, fetch });

	// Authoritative "no session": the visitor is a guest.
	if (response?.status === 401 || response?.status === 403) {
		return { user: null };
	}

	// Any other failure (network, 5xx, empty body) is not an auth verdict, so it
	// must not silently flip a signed-in user to guest — fail the load instead.
	if (error || !data) {
		throwApiError(error, response, 'Не удалось связаться с сервером');
	}

	return { user: data };
};
