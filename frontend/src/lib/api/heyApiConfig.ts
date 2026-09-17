import type { CreateClientConfig } from '$lib/api/generated/client.gen';

import { PUBLIC_API_URL } from '$env/static/public';

/**
 * Initial configuration for the generated singleton client, wired via the
 * `runtimeConfigPath` option of `@hey-api/client-fetch` (see openapi-ts.config.ts).
 *
 * It runs at client *creation*, so every caller — including the generated
 * `*Options()` TanStack helpers, which capture the singleton at import time —
 * sees the base URL and cookie policy without any boot ordering to get right.
 * Interceptors are registered separately in ./index.ts, which cannot happen here
 * because this module is imported *by* client.gen.ts.
 *
 * @see https://heyapi.dev/docs/openapi/typescript/clients/fetch
 */
export const createClientConfig: CreateClientConfig = (config) => ({
	...config,
	baseUrl: PUBLIC_API_URL,
	credentials: 'include'
});
