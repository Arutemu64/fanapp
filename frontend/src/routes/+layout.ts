import { version } from '$app/env';
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';
import { defaultShouldDehydrateQuery, QueryClient } from '@tanstack/svelte-query';
import { persistQueryClient } from '@tanstack/svelte-query-persist-client';
import { del, get, set } from 'idb-keyval';

import { getApiErrorCode } from '#lib/api/errors.js';
import {
	getSettingsQueryKey,
	getSyncSourcesQueryKey,
	getUserQueryKey,
	getVotingDashboardQueryKey,
	listBroadcastsQueryKey,
	listFeedbackQueryKey,
	listScheduleChangesQueryKey,
	listUsersQueryKey
} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { currentUserOptions } from '#lib/api/index.js';
import { FIRST_PAINT_TIMEOUT_MS } from '#lib/utils/fetchTimeout.js';

import type { LayoutLoad } from './$types';

// SPA-only: render entirely on the client. There is no server render.
export const ssr = false;

// How long a cached copy may serve the app offline: a festival weekend plus the
// trip there and back, where the persister's 24h default would drop the
// programme for anyone who didn't open the app for a day. StaleDataNotice shows
// how old what's on screen is. gcTime must be at least this, or unused queries
// are garbage-collected before they are ever persisted:
// https://tanstack.com/query/latest/docs/framework/react/plugins/persistQueryClient
const CACHE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;

// Staff tools are online-only (tools/+layout.ts), so a saved copy of them buys
// nothing offline — and the user directory, cards and feedback would leave
// other people's details on the device for the cache's whole lifetime. Kept in
// memory, never written to IndexedDB. Identified by operation id, the first
// part of every hey-api query key.
const ONLINE_ONLY_QUERY_IDS = new Set(
	[
		getSettingsQueryKey(),
		getVotingDashboardQueryKey(),
		getSyncSourcesQueryKey(),
		listUsersQueryKey(),
		getUserQueryKey({ path: { user_id: '' } }),
		listFeedbackQueryKey(),
		listBroadcastsQueryKey(),
		listScheduleChangesQueryKey()
	].map(([{ _id }]) => _id)
);

// Runs once per page load: nothing here reads `url` or calls `depends`, and the
// app never calls `invalidateAll`/`refreshAll`, so the QueryClient — and the
// cache in it — lives for the whole session. It is load data rather than a
// module singleton (TanStack's SvelteKit setup:
// https://tanstack.com/query/latest/docs/framework/svelte/ssr), so it never
// outlives the document; logout empties it explicitly (forgetSession).
export const load: LayoutLoad = async () => {
	const queryClient = new QueryClient({
		defaultOptions: {
			queries: {
				gcTime: CACHE_MAX_AGE_MS,
				// Data a load prefetched on hover/tap stays fresh when the page mounts a
				// moment later, rather than being refetched straight away
				// (https://tanstack.com/query/latest/docs/framework/react/guides/prefetching).
				// Live data doesn't wait it out: SSE events and mutations invalidate, which
				// refetches regardless of staleTime.
				staleTime: 60 * 1000,
				// Retry only a request that got no API answer — a network failure, a
				// timeout, a gateway page. An API error (401, 404, validation) is the
				// server's verdict, and repeating it only delays showing it by seconds.
				retry: (failureCount, error) => failureCount < 3 && getApiErrorCode(error) === undefined
			}
		}
	});

	// One IndexedDB entry holds the whole cache, so every screen that has loaded
	// once also opens offline. Restored before any guard reads identity from it.
	// The build `version` busts it on deploy, so a client never reads a payload
	// shaped by an older API.
	const [, restored] = persistQueryClient({
		queryClient,
		persister: createAsyncStoragePersister({
			storage: { getItem: get, setItem: set, removeItem: del }
		}),
		maxAge: CACHE_MAX_AGE_MS,
		buster: version,
		dehydrateOptions: {
			shouldDehydrateQuery: (query) => {
				const [{ _id }] = query.queryKey as [{ _id: string }];
				return defaultShouldDehydrateQuery(query) && !ONLINE_ONLY_QUERY_IDS.has(_id);
			}
		}
	});
	await restored;

	// Identity gates the route guards, so settle it before any child load reads
	// it. A restored user answers at once (the components reading it revalidate);
	// only a first boot waits on /me, and no longer than first paint can afford on
	// a stalled network — the request keeps going and lands in the cache anyway.
	const firstPaintBudget = new Promise((resolve) => setTimeout(resolve, FIRST_PAINT_TIMEOUT_MS));
	await Promise.race([
		queryClient.query({ ...currentUserOptions(), staleTime: 'static' }),
		firstPaintBudget
	]).catch(() => {});

	return { queryClient };
};
