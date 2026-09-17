import type { ResolvedRequestOptions } from '$lib/api/generated/client';

import { client } from '$lib/api/generated/client.gen';
import {
	isBackendUnreachableStatus,
	markReachable,
	probeReachability
} from '$lib/services/reachability';

// True while a 401-triggered identity refresh is in flight, so a burst of
// rejected calls collapses into a single refetch. A transient concurrency
// latch — not user/session state, so it is safe as module state in this
// client-only SPA.
let reconcilingSession = false;

// Set by the root layout once it has built the QueryClient. The api module must
// not hold the client itself: a QueryClient caches user-scoped data and would
// outlive login/logout as a module singleton. This is only the wiring — a
// transient reference the layout owns and replaces on every boot.
let reconcileSession: (() => Promise<unknown>) | null = null;

/**
 * Register what a 401 should do: re-run the identity query so an expired session
 * flips the whole app to the guest state in one place. Called by the root layout
 * with a closure over the QueryClient it created.
 */
export function onUnauthorized(reconcile: () => Promise<unknown>): void {
	reconcileSession = reconcile;
}

// When any API call is rejected as unauthenticated, refetch identity. An expired
// session then flips the whole app to the guest state in one place — the identity
// query resolves to `null`, per-user queries are dropped, and the (protected)
// guard redirects to /login — instead of every page failing on its own with a
// stale "logged in" UI. Exclusions:
//   - `/me/` delivers the auth verdict itself; reacting to its 401 would
//     re-trigger the same refetch in a loop.
//   - credential logins 401 on a wrong password/code — that is not a session
//     expiry, and the visitor is a guest already. (`/auth/logout` is NOT
//     excluded: a 401 there means the session is already gone — reconciling
//     is exactly what we want.)
const CREDENTIAL_CHECK_PATHS = new Set(['/me/', '/auth/login', '/auth/login-with-code']);

// The response interceptor runs for every response the client receives, before
// it decides ok vs error — so both watches below see 4xx/5xx too, not just 2xx.
// `options.url` is the operation's path template (e.g. `/me/`), not the resolved
// URL, which is what the credential-path exclusion matches against.
function watchResponse(response: Response, _request: Request, options: ResolvedRequestOptions) {
	// A non-gateway response proves the backend answered; 502/503/504 means the
	// proxy is up but the backend behind it is not — same as a network failure.
	markReachable(!isBackendUnreachableStatus(response.status));

	if (response.status !== 401) return response;
	if (CREDENTIAL_CHECK_PATHS.has(options.url)) return response;
	if (reconcilingSession || !reconcileSession) return response;
	reconcilingSession = true;
	// Fire-and-forget so the failing response still settles immediately for its
	// caller — forms keep their own inline 401 error handling.
	void reconcileSession().finally(() => {
		reconcilingSession = false;
	});
	return response;
}

// The error interceptor fires for every non-ok response too, not only thrown
// fetches — but a response (even a 4xx/5xx) already went through `watchResponse`,
// which owns status-based reachability. Only a *thrown* fetch (network failure /
// timeout / abort) carries no response, and that is the ambiguous case — a
// deliberate abort, one flaky request, a CORS hiccup — that must not flip the app
// offline on its own. So probe only when there is no response: kick the
// authoritative health probe and let it render the verdict. Leave the error
// untouched so the caller still sees it.
function watchError(error: unknown, response?: Response): unknown {
	if (!response) {
		void probeReachability();
	}
	return error;
}

// Registered once, at module load, on the singleton the generated `*Options()`
// helpers already close over. Base URL and credentials come from heyApiConfig.ts,
// which runs at client creation; interceptors cannot be set there because that
// module is imported by client.gen.ts.
client.interceptors.response.use(watchResponse);
client.interceptors.error.use(watchError);

export { client };
