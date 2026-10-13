import { invalidate } from '$app/navigation';
import { type QueryClient, queryOptions } from '@tanstack/svelte-query';

import type { ResolvedRequestOptions } from '#lib/api/generated/client/index.js';

import { getCurrentUserQueryKey } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { client } from '#lib/api/generated/client.gen.js';
import { getCurrentUser } from '#lib/api/generated/index.js';
import {
	isBackendUnreachableStatus,
	markReachable,
	probeReachability
} from '#lib/services/reachability.js';
import { isLogoutPending } from '#lib/utils/pendingLogout.js';

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
			// A logout requested offline is still pending server-side (the HttpOnly
			// cookie can't be cleared by JS). Present as logged-out until the queued
			// POST /auth/logout revokes the session — otherwise a still-valid cookie
			// would let /me resurrect the account we just left. The flush
			// (reachabilityMonitor) clears the intent once it succeeds; a fresh login
			// clears it too (completeLogin).
			if (isLogoutPending()) return null;

			const { data, error, response } = await getCurrentUser({ signal });
			if (response?.status === 401 || response?.status === 403) return null;
			if (data === undefined) throw error;
			return data;
		}
	});
}

/**
 * Drop what the previous account left in the cache once the app shows the
 * guest state — after logout and after a session expiry. Queries no screen is
 * using are removed, so the persisted cache stops holding them for the next
 * person on a shared device; the ones on screen refetch as the guest.
 */
export function forgetSession(queryClient: QueryClient): void {
	queryClient.removeQueries({ type: 'inactive' });
	void queryClient.invalidateQueries();
}

// True while a 401-triggered identity refresh is in flight, so a burst of
// rejected calls collapses into a single /me refetch. A transient concurrency
// latch, not user/session state, so it is safe as module state in this
// client-only SPA.
let reconcilingSession = false;

// When any API call is rejected as unauthenticated, re-check identity. An
// expired session then flips the whole app to the guest state in one place —
// the user query turns `null`, the guards re-run (the (protected) one redirects
// to /login) and the previous account's cache is forgotten — instead of every
// page failing on its own with a stale "logged in" UI. Exclusions:
//   - `/me/` delivers the auth verdict itself; reacting to its 401 would
//     re-trigger the same fetch in a loop.
//   - credential logins 401 on a wrong password/code — that is not a session
//     expiry, and the visitor is a guest already. (`/auth/logout` is NOT
//     excluded: a 401 there means the session is already gone — reconciling
//     is exactly what we want.)
const CREDENTIAL_CHECK_PATHS = new Set(['/me/', '/auth/login', '/auth/login-with-code']);

async function reconcileSession(queryClient: QueryClient): Promise<void> {
	const { queryKey } = currentUserOptions();
	const hadUser = Boolean(queryClient.getQueryData(queryKey));
	await queryClient.refetchQueries({ queryKey });
	if (!hadUser || queryClient.getQueryData(queryKey)) return;

	// 'app:current-user' is what the guard loads depend on.
	await invalidate('app:current-user');
	forgetSession(queryClient);
}

/**
 * Watch every API response for reachability and session expiry. Call once from
 * the root layout; returns the teardown, which matters for dev HMR — without it
 * each cycle would stack another pair of interceptors on the shared client.
 */
export function watchApiResponses(queryClient: QueryClient): () => void {
	// The response interceptor runs for every response the client receives, before
	// it decides ok vs error — so it sees 4xx/5xx too, not just 2xx. `options.url`
	// is the operation's path template (e.g. `/me/`), not the resolved URL, which
	// is what the credential-path exclusion matches against.
	const responseId = client.interceptors.response.use(
		(response: Response, _request: Request, options: ResolvedRequestOptions) => {
			// A non-gateway response proves the backend answered; 502/503/504 means the
			// proxy is up but the backend behind it is not — same as a network failure.
			markReachable(!isBackendUnreachableStatus(response.status));

			if (response.status !== 401) return response;
			if (CREDENTIAL_CHECK_PATHS.has(options.url)) return response;
			if (reconcilingSession) return response;
			reconcilingSession = true;
			// Fire-and-forget so the failing response still settles immediately for its
			// caller — forms keep their own inline 401 error handling.
			void reconcileSession(queryClient).finally(() => {
				reconcilingSession = false;
			});
			return response;
		}
	);

	// The error interceptor fires for every non-ok response too, not only thrown
	// fetches — but a response (even a 4xx/5xx) already went through the one above,
	// which owns status-based reachability. Only a *thrown* fetch (network failure /
	// timeout / abort) carries no response, and that is the ambiguous case — a
	// deliberate abort, one flaky request, a CORS hiccup — that must not flip the app
	// offline on its own. So probe only when there is no response: kick the
	// authoritative health probe and let it render the verdict. Leave the error
	// untouched so the caller still sees it.
	const errorId = client.interceptors.error.use((error: unknown, response?: Response) => {
		if (!response) {
			void probeReachability();
		}
		return error;
	});

	return () => {
		client.interceptors.response.eject(responseId);
		client.interceptors.error.eject(errorId);
	};
}
