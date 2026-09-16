import type { Client } from '$lib/api/generated/client';

import { createApiClient } from '$lib/api';
import { createContext } from 'svelte';

const [getClient, setClient] = createContext<Client>();

/**
 * Create the API client the query layer uses and put it in context (call once,
 * in the root layout).
 *
 * Context, not a module singleton: the client carries the 401 session-reconcile
 * and reachability interceptors, and a module-level instance would outlive
 * login/logout in this SPA. One shared instance per app also keeps the generated
 * query keys stable — they embed `baseUrl`, so a call that forgets to pass a
 * client would key against the generated module default (which has none) and
 * silently miss the cache every consumer else hits.
 *
 * `load` functions keep making their own client with `createApiClient()`: they
 * run outside the component tree and must inject SvelteKit's tracked `fetch`.
 */
export function setApiClient(): Client {
	const client = createApiClient();
	setClient(client);
	return client;
}

/** The app's API client. Pass it to every generated `*Options()` / `*QueryKey()` call. */
export function getApiClient(): Client {
	return getClient();
}
