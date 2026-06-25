import type { paths } from '$lib/api/v1';

import { PUBLIC_API_URL } from '$env/static/public';
import createClient from 'openapi-fetch';

export function createApiClient() {
	return createClient<paths>({
		baseUrl: PUBLIC_API_URL,
		credentials: 'include'
	});
}
