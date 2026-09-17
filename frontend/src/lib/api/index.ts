import type { Client, ResolvedRequestOptions } from '$lib/api/generated/client';

import { invalidate } from '$app/navigation';
import { PUBLIC_API_URL } from '$env/static/public';
import { createClient } from '$lib/api/generated/client';
import { client as globalClient } from '$lib/api/generated/client.gen';
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

function attachInterceptors(client: Client): Client {
	client.interceptors.response.use(watchResponse);
	client.interceptors.error.use(watchError);
	return client;
}

export function createApiClient(): Client {
	const client = createClient({
		baseUrl: PUBLIC_API_URL,
		credentials: 'include'
	});
	return attachInterceptors(client);
}

// Configure the generated global `client` — the one the TanStack Query
// `*Options()` helpers call against — with the same baseUrl, credentials and
// interceptors as createApiClient(). Idempotent: interceptor registration is
// guarded so HMR re-runs don't stack duplicates. Called once at app boot from the
// root layout as the data layer migrates onto the generated query helpers.
let globalConfigured = false;

export function configureApiClient(): void {
	globalClient.setConfig({
		baseUrl: PUBLIC_API_URL,
		credentials: 'include'
	});
	if (globalConfigured) return;
	globalConfigured = true;
	attachInterceptors(globalClient);
}
