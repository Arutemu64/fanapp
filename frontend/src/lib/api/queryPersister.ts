import type { PersistedClient, Persister } from '@tanstack/svelte-query-persist-client';

import * as Sentry from '@sentry/sveltekit';
import { del, get, set } from 'idb-keyval';

/** The IndexedDB entry (idb-keyval's default store) holding the offline queries. */
export const QUERY_CACHE_KEY = 'fanfan-query-cache';

// The persistQueryClient subscription saves on every cache event; a burst of
// events (a boot, an SSE invalidation) becomes one write of the latest state.
const SAVE_INTERVAL_MS = 1000;

/**
 * Persists the dehydrated client to IndexedDB as an object, the way TanStack's
 * IndexedDB example does. IndexedDB stores it by structured clone, so there is
 * no JSON round-trip: an `Error` or `Date` in a saved query comes back intact.
 * createAsyncStoragePersister would add only the throttle, and its storage is
 * typed to strings.
 * https://tanstack.com/query/latest/docs/framework/react/plugins/persistQueryClient#building-a-persister
 */
export function createIdbPersister(): Persister {
	let latest: PersistedClient | undefined;
	let saveTimer: ReturnType<typeof setTimeout> | undefined;

	function save() {
		saveTimer = undefined;
		// A value structured clone rejects (a function or a Headers in a query key)
		// fails the write and leaves the previous save in place.
		set(QUERY_CACHE_KEY, latest).catch((error: unknown) => {
			Sentry.captureException(error, { tags: { source: 'query-persister' } });
		});
	}

	return {
		persistClient(client) {
			latest = client;
			saveTimer ??= setTimeout(save, SAVE_INTERVAL_MS);
		},
		restoreClient: () => get<PersistedClient>(QUERY_CACHE_KEY),
		removeClient: () => del(QUERY_CACHE_KEY)
	};
}
