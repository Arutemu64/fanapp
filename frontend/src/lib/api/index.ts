import type { QueryClient } from '@tanstack/svelte-query';

import { getCurrentUserQueryKey } from '$lib/api/generated/@tanstack/svelte-query.gen';
import { client } from '$lib/api/generated/client.gen';

// When any API call is rejected as unauthenticated, invalidate the identity
// query. An expired session then flips the whole app to the guest state in one
// place — `getCurrentUser` refetches, resolves to a guest, and the (protected)
// guard redirects to /login — instead of every page failing on its own with a
// stale "logged in" UI. Exclusions:
//   - `/me/` delivers the auth verdict itself; reacting to its 401 would
//     re-trigger the same query in a loop.
//   - credential logins 401 on a wrong password/code — that is not a session
//     expiry, and the visitor is a guest already. (`/auth/logout` is NOT
//     excluded: a 401 there means the session is already gone — reconciling
//     is exactly what we want.)
const CREDENTIAL_CHECK_PATHS = new Set(['/me/', '/auth/login', '/auth/login-with-code']);

/**
 * Wire the generated client's 401 handling to `queryClient`.
 *
 * Called from the root `load`, which owns the QueryClient. Interceptors are
 * cleared first so a re-run replaces the handler instead of stacking a second
 * one bound to a discarded client.
 *
 * An interceptor rather than a `QueryCache` error handler because the decision
 * needs the real HTTP status and the operation's path template, and the SDK's
 * `throwOnError` discards both — it throws the parsed error body alone.
 */
export function attachSessionReconciler(queryClient: QueryClient): void {
	client.interceptors.response.clear();

	// Runs for every response before the client decides ok vs error, so it sees
	// 4xx/5xx too. `options.url` is the operation's path template (e.g. `/me/`),
	// not the resolved URL, which is what the exclusion matches against.
	client.interceptors.response.use((response, _request, options) => {
		if (response.status !== 401) return response;
		if (CREDENTIAL_CHECK_PATHS.has(options.url)) return response;

		// Fire-and-forget so the failing response still settles immediately for its
		// caller — forms keep their own inline 401 error handling. A burst of
		// rejected calls collapses on its own: invalidateQueries dedupes concurrent
		// refetches of the same key.
		void queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() });
		return response;
	});
}
