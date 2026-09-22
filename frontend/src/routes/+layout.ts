import { attachSessionReconciler } from '$lib/api';
import {
	getScheduleOptions,
	getSubscriptionsOptions
} from '$lib/api/generated/@tanstack/svelte-query.gen';
import { createQueryClient } from '$lib/api/queryClient';
import { currentUserQueryOptions } from '$lib/api/session';
import { isLogoutPending } from '$lib/utils/pendingLogout';

import type { LayoutLoad } from './$types';

// SPA-only: render entirely on the client. There is no server render.
export const ssr = false;

export const load: LayoutLoad = async () => {
	// One QueryClient per app boot, created here rather than at module scope: it
	// holds the signed-in user's cached data, and modules outlive login/logout in
	// this SPA. Child loads reach it through `await parent()`.
	const queryClient = createQueryClient();
	attachSessionReconciler(queryClient);

	// A logout requested offline is still pending server-side (the HttpOnly cookie
	// can't be cleared by JS). Present as logged-out until the queued POST
	// /auth/logout revokes the session — otherwise a still-valid cookie would let
	// /me resurrect the account we just left. The flush (OfflineService) clears the
	// intent once it succeeds; a fresh login clears it too (completeLogin).
	if (isLogoutPending()) {
		return { queryClient, user: null };
	}

	// `ensureQueryData` reads the (persisted) cache when it is fresh and fetches
	// otherwise, so an offline boot still resolves an identity. A thrown error is
	// the "reachable but no verdict" case — do NOT downgrade to guest, since that
	// would send a signed-in user to /login on one flaky request.
	const user = await queryClient
		.ensureQueryData(currentUserQueryOptions())
		.catch(() => queryClient.getQueryData(currentUserQueryOptions().queryKey) ?? null);

	// Warm the caches the offline routes read, so they are viewable even if the
	// user never opens those pages. Fire-and-forget so first paint is never
	// blocked; `staleTime` makes this a no-op once warm, and the page's own
	// prefetch deduplicates against it rather than issuing a second request.
	void queryClient.prefetchQuery(getScheduleOptions());
	if (user) {
		void queryClient.prefetchQuery(getSubscriptionsOptions());
	}

	return { queryClient, user };
};
