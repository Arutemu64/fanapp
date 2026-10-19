import type { QueryKey } from '@tanstack/svelte-query';
import type { PersistedClient, Persister } from '@tanstack/svelte-query-persist-client';

import * as Sentry from '@sentry/sveltekit';
import { del, get, set } from 'idb-keyval';

/** The IndexedDB entry (idb-keyval's default store) holding the offline queries. */
export const QUERY_CACHE_KEY = 'fanfan-query-cache';

/**
 * The `buster` for persistQueryClient: bump it only when what this persister
 * stores changes form, which discards everything, queued writes included. An
 * API change needs no bump: each saved query carries its response shape's hash,
 * and only the queries whose hash changed are dropped (`schemaHashOf` below).
 */
export const QUERY_CACHE_FORMAT = 'per-query-schema-1';

// The persistQueryClient subscription saves on every cache event; a burst of
// events (a boot, an SSE invalidation) becomes one write of the latest state.
const SAVE_INTERVAL_MS = 1000;

interface StoredCache {
	client: PersistedClient;
	/** queryHash → the response schema hash the query was saved under. */
	schemaHashes: Record<string, string>;
}

interface IdbPersisterOptions {
	/** The current build's response schema hash for a query, if it has one. */
	schemaHashOf: (queryKey: QueryKey) => string | undefined;
}

/**
 * Persists the dehydrated client to IndexedDB as an object, the way TanStack's
 * IndexedDB example does. IndexedDB stores it by structured clone, so there is
 * no JSON round-trip: an `Error` or `Date` in a saved query comes back intact.
 * createAsyncStoragePersister would add only the throttle, and its storage is
 * typed to strings.
 * https://tanstack.com/query/latest/docs/framework/react/plugins/persistQueryClient#building-a-persister
 *
 * Each saved query is stamped with its response schema hash. On restore a query
 * whose hash differs from this build's (the API changed that response's shape)
 * or that has none is left out, so the build never reads a body its types don't
 * describe — while the rest of the cache, and the paused mutations, survive.
 */
export function createIdbPersister({ schemaHashOf }: IdbPersisterOptions): Persister {
	let latest: StoredCache | undefined;
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
			const schemaHashes: Record<string, string> = {};
			for (const query of client.clientState.queries) {
				const hash = schemaHashOf(query.queryKey);
				if (hash !== undefined) schemaHashes[query.queryHash] = hash;
			}
			latest = { client, schemaHashes };
			saveTimer ??= setTimeout(save, SAVE_INTERVAL_MS);
		},
		async restoreClient() {
			const stored = await get<StoredCache>(QUERY_CACHE_KEY);
			// An entry saved before queries carried their hash is a bare client; its
			// buster is an old build's, so persistQueryClient would discard it anyway.
			if (stored?.schemaHashes === undefined) return undefined;

			const { client, schemaHashes } = stored;
			const queries = client.clientState.queries.filter((query) => {
				const current = schemaHashOf(query.queryKey);
				return current !== undefined && schemaHashes[query.queryHash] === current;
			});
			return { ...client, clientState: { ...client.clientState, queries } };
		},
		removeClient: () => del(QUERY_CACHE_KEY)
	};
}
