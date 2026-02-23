import createClient from 'openapi-fetch';
import type { paths } from '$lib/api/v1';
import { PUBLIC_API_URL } from '$env/static/public';
import { refreshTokenMiddleware } from './middlewares';

// Client for browser-side requests (through Caddy)
export const client = createClient<paths>({
	baseUrl: PUBLIC_API_URL,
	credentials: 'include'
});

client.use(refreshTokenMiddleware);

// Register the middleware with the correct refresh endpoint
// client.use(createRefreshTokenMiddleware(`${PUBLIC_API_URL}/auth/refresh`));
