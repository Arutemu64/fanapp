import createClient from 'openapi-fetch';
import type { paths } from '$lib/api/v1';
import { PUBLIC_API_URL } from '$env/static/public';
import { createRefreshTokenMiddleware } from './middlewares';

export function createApiClient() {
	const c = createClient<paths>({
		baseUrl: PUBLIC_API_URL,
		credentials: 'include'
	});
	c.use(createRefreshTokenMiddleware());
	return c;
}

export const client = createApiClient();
