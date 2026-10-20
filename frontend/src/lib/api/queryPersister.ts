import type { PersistedClient, Persister } from '@tanstack/svelte-query-persist-client';

import * as Sentry from '@sentry/sveltekit';
import { del, get, set } from 'idb-keyval';

/** The IndexedDB entry (idb-keyval's default store) holding the offline queries. */
export const QUERY_CACHE_KEY = 'fanfan-query-cache';

// The persistQueryClient subscription saves on every cache event; a burst of
// events (a boot, an SSE invalidation) becomes one write of the latest state.
const SAVE_INTERVAL_MS = 1000;

/**
 * What a write would change on disk. The subscription dehydrates on every cache
 * event — a fetch starting, a screen subscribing, a poll of a query that is never
 * saved — and most of them leave the saved queries and queued writes as they
 * were, yet each write structured-clones the whole programme on the main thread.
 * fetchStatus is left out on purpose: restore resets it, so a fetch starting or
 * ending changes nothing worth saving.
 */
function fingerprint(client: PersistedClient): string {
	const queries = client.clientState.queries.map(({ queryHash, state }) => [
		queryHash,
		state.dataUpdatedAt,
		state.errorUpdatedAt,
		state.isInvalidated
	]);
	const mutations = client.clientState.mutations.map(({ mutationKey, state }) => [
		mutationKey,
		state.submittedAt,
		state.status,
		state.isPaused,
		state.failureCount
	]);
	return JSON.stringify([client.buster, queries, mutations]);
}

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
	// Of the client last written or waiting to be; undefined forces the next write.
	let latestFingerprint: string | undefined;
	let saveTimer: ReturnType<typeof setTimeout> | undefined;

	function save() {
		saveTimer = undefined;
		const writtenFingerprint = latestFingerprint;
		// A value structured clone rejects (a function or a Headers in a query key)
		// fails the write and leaves the previous save in place.
		set(QUERY_CACHE_KEY, latest).catch((error: unknown) => {
			Sentry.captureException(error, { tags: { source: 'query-persister' } });
			// Not on disk, so the next cache event tries again.
			if (latestFingerprint === writtenFingerprint) {
				latestFingerprint = undefined;
			}
		});
	}

	return {
		persistClient(client) {
			const clientFingerprint = fingerprint(client);
			if (clientFingerprint === latestFingerprint) return;
			latest = client;
			latestFingerprint = clientFingerprint;
			saveTimer ??= setTimeout(save, SAVE_INTERVAL_MS);
		},
		restoreClient: () => get<PersistedClient>(QUERY_CACHE_KEY),
		removeClient: () => {
			latestFingerprint = undefined;
			return del(QUERY_CACHE_KEY);
		}
	};
}
