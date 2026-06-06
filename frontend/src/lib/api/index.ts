import createClient from 'openapi-fetch';
import type { paths } from '$lib/api/v1';
import { env } from '$env/dynamic/public';

export function createApiClient() {
	return createClient<paths>({
		baseUrl: env.PUBLIC_API_URL,
		credentials: 'include'
	});
}
