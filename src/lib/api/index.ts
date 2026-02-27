import createClient from 'openapi-fetch';
import type { paths } from '$lib/api/v1';
import { PUBLIC_API_URL } from '$env/static/public';
import { createRefreshTokenMiddleware } from './middlewares';

// For server-side requests always create a new client
export function createApiClient() {
	const c = createClient<paths>({
		baseUrl: PUBLIC_API_URL,
		credentials: 'include'
	});
	c.use(createRefreshTokenMiddleware());
	return c;
}

// Browser-side singleton (safe: each browser tab is a single user)
export const client = createApiClient();
