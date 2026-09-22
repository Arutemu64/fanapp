import { QueryClient } from '@tanstack/svelte-query';

/**
 * How long an unused query stays in the cache.
 *
 * This is the load-bearing setting for offline access, not a memory tuning knob:
 * the persister only writes out queries the cache still holds, so anything
 * garbage-collected during the session is missing from the dehydrated snapshot
 * and unavailable on the next offline boot. A day covers a festival's overnight
 * gap between one visit and the next.
 */
export const PERSISTED_GC_TIME_MS = 24 * 60 * 60 * 1000;

// Long enough that the app shell's repeated reads (bell, schedule, config) don't
// each re-hit the API during one burst of navigation, short enough that a user
// returning to a tab after a few minutes sees current data. The SSE stream owns
// the "something actually changed" signal, so this is only a backstop.
const DEFAULT_STALE_TIME_MS = 30 * 1000;

/**
 * The app's single QueryClient.
 *
 * Created per app boot in the root `load` (never as a module singleton) because
 * it holds the signed-in user's cached data and modules outlive login/logout in
 * this SPA.
 */
export function createQueryClient(): QueryClient {
	return new QueryClient({
		defaultOptions: {
			mutations: {
				// Queue a mutation fired while offline rather than failing it outright;
				// it runs when connectivity returns.
				networkMode: 'offlineFirst'
			},
			queries: {
				gcTime: PERSISTED_GC_TIME_MS,
				// Serve the persisted copy and still try the network, instead of pausing
				// the query. Every route must render offline from its last synced data —
				// the whole point of the PWA — and a paused query renders nothing.
				networkMode: 'offlineFirst',
				// One retry only: a route already falls back to its persisted copy, so
				// further retries just delay the offline render.
				retry: 1,
				staleTime: DEFAULT_STALE_TIME_MS
			}
		}
	});
}
