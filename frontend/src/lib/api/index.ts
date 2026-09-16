import type { Client, ResolvedRequestOptions } from '$lib/api/generated/client';

import { invalidate } from '$app/navigation';
import { PUBLIC_API_URL } from '$env/static/public';
import { createClient } from '$lib/api/generated/client';
import {
	isBackendUnreachableStatus,
	markReachable,
	probeReachability
} from '$lib/services/reachability';

// True while a 401-triggered identity refresh is in flight, so a burst of
// rejected calls collapses into a single `invalidate`. A transient concurrency
// latch shared by all client instances — not user/session state, so it is safe
// as module state in this client-only SPA.
let reconcilingSession = false;

// When any API call is rejected as unauthenticated, re-run the root layout's
// identity load (`app:current-user`). An expired session then flips the whole
// app to the guest state in one place — the layout caches `null`, per-user
// caches are cleared, and the (protected) guard redirects to /login — instead
// of every page failing on its own with a stale "logged in" UI. Exclusions:
//   - `/me/` delivers the auth verdict itself; reacting to its 401 would
//     re-trigger the same load in a loop.
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
	if (reconcilingSession) return response;
	reconcilingSession = true;
	// Fire-and-forget so the failing response still settles immediately for its
	// caller — forms keep their own inline 401 error handling.
	void invalidate('app:current-user').finally(() => {
		reconcilingSession = false;
	});
	return response;
}

// A thrown fetch (network failure / timeout / abort) yields no Response, so the
// response interceptor never runs. A single rejection is ambiguous, though — a
// deliberate abort, one flaky request, a CORS hiccup — so it must not flip the
// whole app offline on its own. Kick the authoritative health probe instead and
// let it render the verdict; leave the error untouched so the caller still sees it.
function watchError(error: unknown): unknown {
	void probeReachability();
	return error;
}

export function createApiClient(): Client {
	const client = createClient({
		baseUrl: PUBLIC_API_URL,
		credentials: 'include'
	});
	client.interceptors.response.use(watchResponse);
	client.interceptors.error.use(watchError);
	return client;
}
