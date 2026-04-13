import createClient from 'openapi-fetch';
import type { paths } from '$lib/api/v1';
import { PUBLIC_API_URL } from '$env/static/public';

export function createApiClient() {
	return createClient<paths>({
		baseUrl: PUBLIC_API_URL,
		credentials: 'include'
	});
}

export const client = createApiClient();
