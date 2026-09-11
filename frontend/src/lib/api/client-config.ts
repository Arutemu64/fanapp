import { invalidate } from '$app/navigation';
import { PUBLIC_API_URL } from '$env/static/public';
import { isBackendUnreachableStatus, markReachable } from '$lib/services/reachability';

import { client } from './client/client.gen';

/**
 * Configures the shared hey-api client (base URL, credentials, reachability
 * watch, session-expiry reconciliation) — see
 * docs/sketches/hey-api-tanstack-query-migration.md for the shape of this
 * stack.
 *
 * `client` from `client.gen.ts` is a stateless HTTP transport (base URL,
 * credentials, interceptors) — it carries no per-user data, so configuring it
 * once at module scope does not violate the no-singleton rule for user/session
 * state (docs/api.md "Client Isolation"). Per-user data lives in the
 * `QueryClient`'s cache instead (see `queryClient.ts`), cleared on logout there
 * — mirroring `clearUserCache()`.
 */

client.setConfig({
	baseUrl: PUBLIC_API_URL,
	credentials: 'include'
});

// True while a 401-triggered identity refresh is in flight, so a burst of
// rejected calls collapses into a single `invalidate`. A transient concurrency
// latch shared by all callers — not user/session state, so it is safe as
// module state in this client-only SPA.
let reconcilingSession = false;

// When any API call is rejected as unauthenticated, re-run the root layout's
// identity query. An expired session then flips the whole app to the guest
// state in one place instead of every page failing on its own with a stale
// "logged in" UI.
//   - `/me/` delivers the auth verdict itself; reacting would loop.
//   - the credential logins 401 on a wrong password/code — not a session
//     expiry, and the visitor is a guest already.
const CREDENTIAL_CHECK_PATHS = new Set(['/me/', '/auth/login', '/auth/login-with-code']);

client.interceptors.response.use((response, _request, opts) => {
	// A non-gateway response proves the backend answered; 502/503/504 means the
	// proxy is up but the backend behind it is not — same as a network failure.
	markReachable(!isBackendUnreachableStatus(response.status));

	if (response.status === 401 && !CREDENTIAL_CHECK_PATHS.has(opts.url) && !reconcilingSession) {
		reconcilingSession = true;
		// Fire-and-forget so the failing response still settles immediately for
		// its caller — forms keep their own inline 401 error handling.
		void invalidate('app:current-user').finally(() => {
			reconcilingSession = false;
		});
	}

	return response;
});

// `throwOnError: true` (set by every generated TanStack query/mutation option)
// throws the parsed error body alone, without the `Response` — so a call site
// that needs the HTTP status for branching (e.g. 401/403/404/422 → distinct
// Russian copy, as `tools/settings` does) has nothing to read it from. Stamp it
// on here once, globally, rather than in every consumer.
client.interceptors.error.use((error, response) => {
	const base = typeof error === 'object' && error !== null ? error : { detail: error };
	// `response` is undefined for a genuine network failure (no HTTP exchange at
	// all) — leave `status` unset rather than fabricating one; callers already
	// treat a missing status as "not a mapped HTTP error".
	return response ? { ...base, status: response.status } : base;
});

export { client };
