import type { CreateClientConfig } from '$lib/api/generated/client.gen';

import { PUBLIC_API_URL } from '$env/static/public';

/**
 * Initial configuration for the generated module-level client, applied by
 * `client.gen.ts` before any request is made (Hey API's `runtimeConfigPath`).
 *
 * Doing it here rather than in app code means a `*Options()` helper handed
 * straight to TanStack Query already points at the API with the session cookie
 * attached — there is no second, separately configured client to drift from.
 */
export const createClientConfig: CreateClientConfig = (config) => ({
	...config,
	baseUrl: PUBLIC_API_URL,
	credentials: 'include'
});
