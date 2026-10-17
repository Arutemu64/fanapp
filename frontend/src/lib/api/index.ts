import {
	CancelledError,
	type QueryClient,
	type QueryExecuteOptions,
	type QueryKey
} from '@tanstack/svelte-query';

import type { ResolvedRequestOptions } from '#lib/api/generated/client/index.js';

import { getApiErrorCode, gotNoApiAnswer } from '#lib/api/errors.js';
import { getCurrentUserQueryKey } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { client } from '#lib/api/generated/client.gen.js';
import {
	isBackendUnreachableStatus,
	markReachable,
	probeReachability
} from '#lib/services/reachability.js';
import { FIRST_PAINT_TIMEOUT_MS } from '#lib/utils/fetchTimeout.js';

/**
 * Run a query a `load` waits for, bounded so a navigation can't hang. A load has
 * no component to show progress, so the request runs at once and once only —
 * no retries, and no pausing until reachability recovers (`networkMode:
 * 'always'`) — and rejects with a TimeoutError (`isConnectionFailure`) after
 * the first-paint budget. A request still running then keeps going and lands in
 * the cache.
 */
export function queryForLoad<TData, TError, TQueryKey extends QueryKey>(
	queryClient: QueryClient,
	options: QueryExecuteOptions<TData, TError, TData, TData, TQueryKey>
): Promise<TData> {
	let timer: ReturnType<typeof setTimeout> | undefined;
	const budget = new Promise<never>((_, reject) => {
		timer = setTimeout(
			() => reject(new DOMException('signal timed out', 'TimeoutError')),
			FIRST_PAINT_TIMEOUT_MS
		);
	});
	const query = queryClient.query({ ...options, retry: false, networkMode: 'always' });
	return Promise.race([query, budget]).finally(() => clearTimeout(timer));
}

// A 401 means the session may have ended; /me/ gives the verdict. Its own 401
// ends the session — whenever it comes: a restored user whose session expired
// while the app was closed, a refetch on focus, or the check any other 401
// triggers below. An expired session then flips the whole app to the guest
// state in one place instead of every page failing on its own with a stale
// "logged in" UI. The credential logins are excluded: they 401 on a wrong
// password/code, which is not a session expiry, and the visitor is a guest
// already. (`/auth/logout` is NOT excluded: a 401 there means the session is
// already gone — checking is exactly what we want.)
const IDENTITY_PATH = '/me/';
const CREDENTIAL_CHECK_PATHS = new Set(['/auth/login', '/auth/login-with-code']);

// A 401 is session expiry, which `watchApiResponses` already turns into the
// guest state; a toast on top would only repeat it.
const SESSION_ERROR_CODES = new Set(['AUTHENTICATION_ERROR', 'USER_NOT_AUTHENTICATED']);

/**
 * Call `onFailure` when a refresh fails for a query on screen that still shows
 * its last good data — the one failure no page renders, since every page keeps
 * stale data over an error (https://tkdodo.eu/blog/react-query-error-handling).
 * A missing answer is left to the connection banner, and a query that is fine
 * staying quiet (a glanceable poll) opts out with `meta: { quietRefetchErrors: true }`.
 * Returns the teardown.
 */
export function watchBackgroundRefetchErrors(
	queryClient: QueryClient,
	onFailure: () => void
): () => void {
	return queryClient.getQueryCache().subscribe((event) => {
		if (event.type !== 'updated' || event.action.type !== 'error') return;

		const { query } = event;
		const error: unknown = event.action.error;
		if (query.state.data === undefined || query.getObserversCount() === 0) return;
		// «Показать ещё» failing is a next-page fetch, not a refresh: the feed that
		// asked for it shows its own error, and a second toast would repeat it.
		if (query.state.fetchMeta?.fetchMore) return;
		if (query.meta?.quietRefetchErrors === true) return;
		if (gotNoApiAnswer(error) || error instanceof CancelledError) return;
		if (SESSION_ERROR_CODES.has(getApiErrorCode(error) ?? '')) return;

		onFailure();
	});
}

/**
 * Watch every API response for reachability and session expiry. Call once from
 * the root layout; returns the teardown, which matters for dev HMR — without it
 * each cycle would stack another pair of interceptors on the shared client.
 */
export function watchApiResponses(
	queryClient: QueryClient,
	onSessionExpired: () => void
): () => void {
	// The response interceptor runs for every response the client receives, before
	// it decides ok vs error — so it sees 4xx/5xx too, not just 2xx. `options.url`
	// is the operation's path template (e.g. `/me/`), not the resolved URL, which
	// is what the path checks match against.
	const responseId = client.interceptors.response.use(
		(response: Response, _request: Request, options: ResolvedRequestOptions) => {
			// A non-gateway response proves the backend answered; 502/503/504 means the
			// proxy is up but the backend behind it is not — same as a network failure.
			markReachable(!isBackendUnreachableStatus(response.status));

			if (response.status !== 401) return response;
			if (CREDENTIAL_CHECK_PATHS.has(options.url)) return response;
			// Fire-and-forget so the failing response still settles immediately for its
			// caller — forms keep their own inline 401 error handling.
			if (options.url === IDENTITY_PATH) {
				onSessionExpired();
			} else {
				// Joins a /me/ fetch already in flight, so a burst of 401s asks once.
				void queryClient.refetchQueries(
					{ queryKey: getCurrentUserQueryKey() },
					{ cancelRefetch: false }
				);
			}
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
