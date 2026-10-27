import type { PersistedClient, Persister } from '@tanstack/svelte-query-persist-client';

import * as Sentry from '@sentry/sveltekit';
import { del, get, set } from 'idb-keyval';

export const QUERY_CACHE_KEY = 'fanfan-query-cache';

const SAVE_INTERVAL_MS = 1000;

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

export function createIdbPersister(): Persister {
	let latest: PersistedClient | undefined;
	let latestFingerprint: string | undefined;
	let saveTimer: ReturnType<typeof setTimeout> | undefined;

	function save() {
		saveTimer = undefined;
		const writtenFingerprint = latestFingerprint;
		set(QUERY_CACHE_KEY, latest).catch((error: unknown) => {
			Sentry.captureException(error, { tags: { source: 'query-persister' } });
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
