import { createApiClient } from '$lib/api';

import { readStorage, removeStorage, writeStorage } from './safeStorage';

/**
 * A logout the user requested while offline.
 *
 * The session lives in an HttpOnly cookie, so JS cannot clear it. A purely local
 * logout (drop the caches, show guest UI) would therefore be dishonest: the
 * cookie is still valid, so the next reachable `/me` would silently restore the
 * session. So we persist the *intent* and fire `POST /auth/logout` — which
 * deletes the cookie and revokes the Redis session — once the backend is
 * reachable again (on the offline→online edge and on a fresh boot).
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
 * Marks that an OAuth re-auth is starting while a logout is still pending, so the
 * return boot can tell a *successful* new session (drop the stale intent, don't
 * revoke it) from a cancelled one (keep the intent — the old session was never
 * revoked). Session-scoped on purpose: abandoning the flow by closing the app
 * clears the marker, so the pending revoke is then honoured as normal.
 */
const REAUTH_ATTEMPT_KEY = 'fanfan:reauth-attempt';

/** Record that an OAuth re-auth is starting (call only when a logout is pending). */
export function markReauthAttempt(): void {
	writeStorage('session', REAUTH_ATTEMPT_KEY, '1');
}

/** Read and clear the re-auth marker; true if a re-auth was in flight. */
export function consumeReauthAttempt(): boolean {
	const attempted = readStorage('session', REAUTH_ATTEMPT_KEY) === '1';
	if (attempted) removeStorage('session', REAUTH_ATTEMPT_KEY);
	return attempted;
}

/**
 * Fire a queued offline logout, if one is pending. Clears the intent on any
 * definitive outcome — a 2xx, or a 401/403 that means the session is already
 * gone. A network failure (still offline) or a 5xx leaves it pending so the next
 * reconnect retries. Safe to call concurrently: the endpoint is idempotent.
 */
export async function flushPendingLogout(): Promise<void> {
	if (!isLogoutPending()) return;

	const client = createApiClient();
	try {
		const { response } = await client.POST('/auth/logout');
		if (response.ok || response.status === 401 || response.status === 403) {
			clearLogoutPending();
		}
		// Any other status (e.g. 5xx): keep the intent and retry on the next edge.
	} catch {
		// Still unreachable — keep the intent for the next reconnect.
	}
}
