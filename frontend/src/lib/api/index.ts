import type { paths } from '$lib/api/schema';
import type { Middleware } from 'openapi-fetch';

import { invalidate } from '$app/navigation';
import { PUBLIC_API_URL } from '$env/static/public';
import createClient from 'openapi-fetch';

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

const sessionExpiryWatch: Middleware = {
	onResponse({ response, schemaPath }) {
		if (response.status !== 401) return;
		if (CREDENTIAL_CHECK_PATHS.has(schemaPath)) return;
		if (reconcilingSession) return;
		reconcilingSession = true;
		// Fire-and-forget so the failing response still settles immediately for
		// its caller — forms keep their own inline 401 error handling.
		void invalidate('app:current-user').finally(() => {
			reconcilingSession = false;
		});
	}
};

export function createApiClient() {
	const client = createClient<paths>({
		baseUrl: PUBLIC_API_URL,
		credentials: 'include'
	});
	client.use(sessionExpiryWatch);
	return client;
}
