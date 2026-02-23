import createClient from 'openapi-fetch';
import type { paths } from '$lib/api/v1';
import { PRIVATE_API_URL } from '$env/static/private';

// Server-only client - direct to FastAPI, bypassing Caddy
export const serverClient = createClient<paths>({
	baseUrl: PRIVATE_API_URL,
	credentials: 'include'
});
