import { createApiClient } from '$lib/api';
import { readCache, writeCache } from '$lib/utils/offlineCache';
import { timeoutSignal, FIRST_PAINT_TIMEOUT_MS } from '$lib/utils/fetchTimeout';
import { isReachable, markReachable } from '$lib/services/reachability';
import type { CurrentUserDTO } from '$lib/types/user';
import type { LayoutLoad } from './$types';

// SPA-only: render entirely on the client. No SSR, no server load.
export const ssr = false;

// Single current-session user; cached so the app can still boot offline.
const USER_CACHE_KEY = 'me:user';

async function cachedUser() {
	const cached = await readCache<CurrentUserDTO | null>(USER_CACHE_KEY);
	return { user: cached ?? null };
}

export const load: LayoutLoad = async ({ fetch, depends }) => {
	depends('app:current-user');

	// Known unreachable (probe/previous load already failed): boot straight from
	// cache instead of blocking first paint on a doomed /me/ request.
	if (!isReachable()) {
		return cachedUser();
	}

	const client = createApiClient();

	try {
		const { data, response, error } = await client.GET('/me/', {
			fetch,
			// Bound the call so a hung network (dead VPN, captive WiFi) can't keep
			// the boot splash spinning for ~a minute before we fall back to cache.
			signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
		});

		// Got an HTTP response → the server is reachable.
		markReachable(true);

		// Guest, or stale/invalid session → treat as not logged in.
		if (response.status === 401 || response.status === 403 || error || !data) {
			void writeCache<CurrentUserDTO | null>(USER_CACHE_KEY, null);
			return { user: null };
		}

		void writeCache<CurrentUserDTO | null>(USER_CACHE_KEY, data);
		return { user: data };
	} catch {
		// Offline / timeout / server unreachable: fall back to the last known user
		// so the root layout still mounts (else the boot splash spins forever).
		markReachable(false);
		return cachedUser();
	}
};
