import { PUBLIC_API_URL } from '$app/env/public';

import type { CreateClientConfig } from './generated/client.gen';

import { fetchRecordingConnectionFailures } from './errors';

// Runtime config for the generated singleton client (`runtimeConfigPath` in
// openapi-ts.config.ts), so every SDK call and every TanStack Query option the
// plugin generates share one base URL and cookie policy without each call site
// passing a client. The session cookie rides along via `credentials: 'include'`.
// `fetch` is wrapped so a dropped connection is told apart from a code bug that
// throws the same TypeError (see `isConnectionFailure`).
export const createClientConfig: CreateClientConfig = (config) => ({
	...config,
	baseUrl: PUBLIC_API_URL,
	credentials: 'include',
	fetch: fetchRecordingConnectionFailures
});
