import { version } from '$app/env';
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';
import { defaultShouldDehydrateQuery, QueryClient } from '@tanstack/svelte-query';
import { persistQueryClient } from '@tanstack/svelte-query-persist-client';
import { del, get, set } from 'idb-keyval';

import { getApiErrorCode } from '#lib/api/errors.js';
import {
	countUnreadNotificationsQueryKey,
	getCurrentUserQueryKey,
	getPublicConfigQueryKey,
	getScheduleQueryKey,
	getSubscriptionsQueryKey,
	listUserNotificationsQueryKey
} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { currentUserOptions } from '#lib/api/index.js';
import { FIRST_PAINT_TIMEOUT_MS } from '#lib/utils/fetchTimeout.js';

import type { LayoutLoad } from './$types';

// SPA-only: render entirely on the client. There is no server render.
export const ssr = false;

// The screens that must open offline: the identity the guards and the profile
// read, the home hero, the programme with the viewer's subscriptions, and the
// notifications with their badge. Only these are written to IndexedDB. Every
// other query is online-only: fetched fresh after a cold start and dropped from
// memory five minutes after its screen closes (TanStack's default gcTime) —
// voting must not show a stale ballot, and the staff tools hold other people's
// details that have no business on the device.
const OFFLINE_QUERY_KEYS = [
	getCurrentUserQueryKey(),
	getPublicConfigQueryKey(),
	getScheduleQueryKey(),
	getSubscriptionsQueryKey(),
	listUserNotificationsQueryKey(),
	countUnreadNotificationsQueryKey()
];
// Matched by operation id, the first part of every hey-api query key, so a
// list key also covers its paginated variant.
const OFFLINE_QUERY_IDS = new Set(OFFLINE_QUERY_KEYS.map(([{ _id }]) => _id));

// How long a cached copy may serve the app offline: a festival weekend plus the
// trip there and back, where the persister's 24h default would drop the
// programme for anyone who didn't open the app for a day. StaleDataNotice shows
// how old what's on screen is. The offline queries keep this gcTime too, or they
// are garbage-collected before they are ever persisted:
// https://tanstack.com/query/latest/docs/framework/react/plugins/persistQueryClient
const CACHE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;

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
	// Set before the restore below: restored queries take their options from here.
	for (const queryKey of OFFLINE_QUERY_KEYS) {
		queryClient.setQueryDefaults(queryKey, { gcTime: CACHE_MAX_AGE_MS });
	}

	// One IndexedDB entry holds the offline queries, so those screens open offline
	// once they have loaded. Restored before any guard reads identity from it.
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
				return defaultShouldDehydrateQuery(query) && OFFLINE_QUERY_IDS.has(_id);
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
