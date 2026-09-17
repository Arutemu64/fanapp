import { onUnauthorized } from '$lib/api';
import { getCurrentUserQueryKey } from '$lib/api/generated/@tanstack/svelte-query.gen';
import {
	currentUserQueryOptions,
	scheduleQueryOptions,
	subscriptionsQueryOptions
} from '$lib/api/queries';
import { clearUserQueries, createQueryClient, restoreQueryCache } from '$lib/api/queryClient';
import { isLogoutPending } from '$lib/utils/pendingLogout';
import { onReconnectRefresh } from '$lib/utils/reconnectRefresh';

import type { LayoutLoad } from './$types';

// SPA-only: render entirely on the client. There is no server render.
export const ssr = false;

// One cache per boot, built here rather than at module scope of a `$lib` module:
// it holds the viewer's data, and a `$lib` singleton would outlive login/logout.
// This module's lifetime is the page load, and `clearUserQueries` drops the
// user-scoped half on logout within it.
let queryClient: ReturnType<typeof createQueryClient> | undefined;
let restored: Promise<unknown> | undefined;

export const load: LayoutLoad = async () => {
	if (!queryClient) {
		queryClient = createQueryClient();

		// Hydrate from IndexedDB before anything queries, so an offline cold boot
		// reads the last synced copy instead of racing the restore into an empty
		// cache. Awaited once; later load re-runs reuse the same promise.
		restored = restoreQueryCache(queryClient);

		// A 401 anywhere in the app re-runs the identity query, so an expired session
		// flips every consumer to the guest state at once.
		const client = queryClient;
		onUnauthorized(() => client.refetchQueries({ queryKey: getCurrentUserQueryKey() }));

		// Connectivity recovered: refetch everything on screen, since live SSE events
		// only carry changes and we were not listening while disconnected.
		onReconnectRefresh(() => void client.invalidateQueries());
	}
	await restored;

	// A logout requested offline is still pending server-side (the HttpOnly cookie
	// can't be cleared by JS). Present as logged-out until the queued POST
	// /auth/logout revokes the session — otherwise a still-valid cookie would let
	// /me resurrect the account we just left. The flush (OfflineService) clears the
	// intent once it succeeds; a fresh login clears it too (completeLogin).
	if (isLogoutPending()) {
		clearUserQueries(queryClient);
		return { queryClient, user: null };
	}

	// `ensureQueryData` rather than `createQuery`: the (protected) guard below this
	// layout has to decide redirect-vs-offline before the route renders, so identity
	// must be resolved in `load`. Components read the same cache entry reactively
	// (see +layout.svelte), so an invalidation still updates the UI everywhere.
	//
	// A rejected identity query is not fatal — it means "reachable but no verdict"
	// or a cold offline boot with nothing cached. Both are the guest state as far as
	// first paint goes; the guard tells them apart from live reachability.
	const user = await queryClient.ensureQueryData(currentUserQueryOptions()).catch(() => null);

	// Warm the programme so it is viewable offline even if the user never opens the
	// schedule page. Fire-and-forget: `ensureQueryData` is a no-op once the entry is
	// fresh, so this never blocks first paint and never refetches on its own.
	void queryClient.ensureQueryData(scheduleQueryOptions()).catch(() => undefined);

	// Same for the viewer's own subscriptions, which the programme rows need to
	// render their reminder badges. Only signed-in users have any.
	if (user) {
		void queryClient.ensureQueryData(subscriptionsQueryOptions()).catch(() => undefined);
	}

	return { queryClient, user };
};
