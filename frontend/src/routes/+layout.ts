import type { CurrentUserDto } from '$lib/api/generated';

import { createApiClient } from '$lib/api';
import { getCurrentUser } from '$lib/api/generated';
import { clearUserCache, fetchWithCache, userScope } from '$lib/utils/offlineCache';
import { isLogoutPending } from '$lib/utils/pendingLogout';

import type { LayoutLoad } from './$types';

// SPA-only: render entirely on the client. There is no server render.
export const ssr = false;

// Single current-session user; cached so the app can still boot offline.
const USER_CACHE_KEY = 'me:user';

export const load: LayoutLoad = async ({ fetch, depends }) => {
	depends('app:current-user');

	// A logout requested offline is still pending server-side (the HttpOnly cookie
	// can't be cleared by JS). Present as logged-out until the queued POST
	// /auth/logout revokes the session — otherwise a still-valid cookie would let
	// /me resurrect the account we just left. The flush (OfflineService) clears the
	// intent once it succeeds; a fresh login clears it too (completeLogin).
	if (isLogoutPending()) {
		return { user: null };
	}

	const client = createApiClient();

	// `null` is a real cached value (logged out); `undefined` means "reachable but
	// no verdict, keep the cached user" (see fetcher below), so the type spans both.
	const { data } = await fetchWithCache<CurrentUserDto | null>({
		key: USER_CACHE_KEY,
		scope: userScope,
		fetcher: async ({ signal }) => {
			const { data, response, error } = await getCurrentUser({ client, fetch, signal });

			// Authoritative "session ended": cache logged-out AND drop per-user caches
			// so no orphaned entries linger for the next account on a shared device.
			// Universal caches (e.g. schedule) are kept warm. Mirrors explicit logout
			// (AppNavbar.handleLogout).
			if (response?.status === 401 || response?.status === 403) {
				void clearUserCache();
				return null;
			}

			// Reachable but not an auth verdict (5xx / parse error / empty body): do NOT
			// downgrade identity. Returning `undefined` keeps the last-good cached user
			// instead of overwriting it with `null` — a transient error must not flip a
			// logged-in user to guest (which would orphan their per-user caches).
			if (error || !data) {
				return undefined;
			}

			return data;
		}
	});

	// A complete cache miss (offline first boot) is also "not logged in".
	const user = data ?? null;

	return { user };
};
