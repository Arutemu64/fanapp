import createClient from 'openapi-fetch';
import type { paths } from '$lib/api/v1';
import { PUBLIC_API_URL } from '$env/static/public';
import { createRefreshTokenMiddleware } from './middlewares';

export function createApiClient() {
	return createClient<paths>({
		baseUrl: PUBLIC_API_URL,
		credentials: 'include'
	});
}

function createBrowserApiClient() {
	const c = createApiClient();
	// SSR refresh lives in hooks.server.ts; this middleware only handles browser-side retries.
	c.use(createRefreshTokenMiddleware());
	return c;
}

// Browser-side singleton. On the server, SSR refresh is handled in hooks.server.ts.
export const client = createBrowserApiClient();
