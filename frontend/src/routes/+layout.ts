import { createApiClient } from '$lib/api';
import type { LayoutLoad } from './$types';

// SPA-only: render entirely on the client. No SSR, no server load.
export const ssr = false;

export const load: LayoutLoad = async ({ fetch, depends }) => {
	depends('app:current-user');

	const client = createApiClient();
	const { data, response, error } = await client.GET('/me/', { fetch });

	// Guest, or stale/invalid session → treat as not logged in.
	if (response.status === 401 || response.status === 403 || error || !data) {
		return { user: null };
	}

	return { user: data };
};
