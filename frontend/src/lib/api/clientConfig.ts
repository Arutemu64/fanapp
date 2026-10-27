import { PUBLIC_API_URL } from '$app/env/public';

import type { CreateClientConfig } from './generated/client.gen';

import { fetchRecordingConnectionFailures } from './errors';

export const createClientConfig: CreateClientConfig = (config) => ({
	...config,
	baseUrl: PUBLIC_API_URL,
	credentials: 'include',
	fetch: fetchRecordingConnectionFailures
});
