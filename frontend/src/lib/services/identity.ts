import { type QueryClient, queryOptions } from '@tanstack/svelte-query';

import { getCurrentUserQueryKey } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { getCurrentUser, logoutUser } from '#lib/api/generated/index.js';
import { queryForLoad } from '#lib/api/index.js';
import { readStorage, removeStorage, writeStorage } from '#lib/utils/safeStorage.js';

/**
 * Who is signed in on this device: the `/me` query, its boot variant, and a
 * logout the user requested while offline. They live together because the
 * pending logout changes what `/me` answers: a reader of either that ignores the
 * other would show a shared phone's last account to the next person.
 *
 * The session lives in an HttpOnly cookie, so JS cannot clear it. A purely local
 * logout (drop the caches, show guest UI) would therefore be dishonest: the
 * cookie is still valid, so the next reachable `/me` would silently restore the
 * session. So we persist the *intent* and fire `POST /auth/logout` — which
 * deletes the cookie and revokes the Redis session — once the backend is
 * reachable again (the root layout flushes on boot and on every recovery).
 *
 * This is one idempotent intent, not a write queue: re-sending the logout is
 * harmless, so there is nothing to order, dedupe or retry-with-backoff. It is
 * persisted (not in-memory) so it survives the app being closed while offline —
 * otherwise the still-valid cookie would outlive the user's decision to leave.
 */
const PENDING_LOGOUT_KEY = 'fanfan:pending-logout';

/** Record that the user logged out while offline; the server revoke is deferred. */
export function markLogoutPending(): void {
	writeStorage('local', PENDING_LOGOUT_KEY, '1');
}

/** True while an offline logout is still waiting to be revoked server-side. */
export function isLogoutPending(): boolean {
	return readStorage('local', PENDING_LOGOUT_KEY) === '1';
}

/**
 * Cancel the pending revoke. Called once it has fired, and on a fresh login —
 * a new session must not be killed by a stale intent from the previous one.
 */
export function clearLogoutPending(): void {
	removeStorage('local', PENDING_LOGOUT_KEY);
}

/**
 * Fire a queued offline logout, if one is pending. Clears the intent on any
 * definitive outcome — a 2xx, or a 401/403 that means the session is already
 * gone. A network failure (still offline) or a 5xx leaves it pending so the next
 * reconnect retries, and so does an aborted `signal`. Safe to call concurrently:
 * the endpoint is idempotent.
 */
export async function flushPendingLogout(signal?: AbortSignal): Promise<void> {
	if (!isLogoutPending()) return;

	// The client never throws: a request that got no answer (still unreachable,
	// timed out) comes back without a `response`, which keeps the intent like a 5xx.
	const { response } = await logoutUser({ signal });
	if (response?.ok || response?.status === 401 || response?.status === 403) {
		clearLogoutPending();
	}
}

/**
 * The signed-in user, or `null` for a guest. Shared by the root load (which
 * settles it before any guard runs), the guards, and every component that
 * renders identity.
 *
 * Only an explicit 401/403 means "guest". Any other failure (5xx, network)
 * throws, and TanStack Query keeps the last good user on error — a transient
 * outage must not flip a logged-in user to guest.
 */
export function currentUserOptions() {
	return queryOptions({
		queryKey: getCurrentUserQueryKey(),
		queryFn: async ({ signal }) => {
			// Present as logged-out until the queued POST /auth/logout revokes the
			// session — otherwise a still-valid cookie would let /me resurrect the
			// account we just left. The flush clears the intent once it succeeds; a
			// fresh login clears it too (Session.loggedIn).
			if (isLogoutPending()) return null;

			const { data, error, response } = await getCurrentUser({ signal });
			if (response?.status === 401 || response?.status === 403) return null;
			// Rethrow the SDK's error as-is, like every generated query does, so the
			// retry rule and error reporting can tell a dropped connection from an
			// API error body.
			if (data === undefined) {
				// eslint-disable-next-line @typescript-eslint/only-throw-error -- the API error body is a plain object
				throw error;
			}
			return data;
		}
	});
}

/**
 * Settle identity into the cache before any guard reads it (root load). Never
 * rejects.
 *
 * A restored user answers at once (the components reading it revalidate, and a
 * /me 401 ends an expired session). A restored guest is re-checked: a social
 * login arrives here as a full page load with a fresh session cookie, and
 * trusting the saved `null` would bounce the new user to /login. A first boot
 * and a guest wait on /me no longer than first paint can afford. A pending
 * offline logout is re-checked too, whose queryFn answers `null` without the
 * network: the logout flag is saved at once but the cache only on the
 * persister's throttle, so a restart in between can restore the account the
 * user just left. A /me that fails leaves the user unknown, which only the
 * (protected) guard has to resolve: it asks the reachability probe itself, so a
 * guest opening Home or the programme on a dead network isn't held on the
 * splash for the probe's offline-confirm window as well.
 */
export async function settleIdentityForBoot(queryClient: QueryClient): Promise<void> {
	await queryForLoad(queryClient, {
		...currentUserOptions(),
		staleTime: (query) => (query.state.data && !isLogoutPending() ? 'static' : 0)
	}).catch(() => {});
}
