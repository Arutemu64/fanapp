import { browser } from '$app/environment';
import { PUBLIC_API_URL } from '$env/static/public';
import type { Middleware } from 'openapi-fetch';

// Header used to prevent infinite retry loops (401 → refresh → 401 → ...).
const RETRY_HEADER = 'x-auth-refresh-retry';

/**
 * Call POST /auth/refresh to get new tokens via cookies.
 * Returns true if the refresh succeeded (browser cookie jar is updated automatically).
 */
async function refreshAccessToken(FnFetch: typeof fetch): Promise<boolean> {
	try {
		const response = await FnFetch(`${PUBLIC_API_URL}/auth/refresh`, {
			method: 'POST',
			credentials: 'include' // Send cookies with the request
		});
		return response.ok;
	} catch (error) {
		console.error('Failed to refresh token:', error);
		return false;
	}
}

/**
 * openapi-fetch middleware that handles browser-side (CSR) token refresh.
 *
 * Flow:
 *   1. On every request, clone the Request (we may need to replay it after refresh).
 *   2. If the response is 401 and it's not an auth endpoint or a retry:
 *      a. Call /auth/refresh to get new cookies.
 *      b. Replay the original request with the new cookies.
 *   3. Concurrent 401s are deduplicated — only one refresh call happens at a time.
 *
 * This middleware is only active in the browser. SSR refresh is handled in hooks.server.ts.
 */
export function createRefreshTokenMiddleware(): Middleware {
	// Store cloned requests so we can replay them after a successful refresh.
	// WeakMap is used because fetch body is single-use — we need a fresh copy for retry.
	const clones = new WeakMap<Request, Request>();

	// Shared promise for deduplicating concurrent refresh attempts.
	let refreshPromise: Promise<boolean> | null = null;

	return {
		onRequest({ request }) {
			clones.set(request, request.clone());
		},

		async onResponse({ request, response, options }) {
			// SSR refresh is handled in hooks.server.ts — skip here to avoid
			// a parallel broken attempt (middleware can't propagate set-cookie to browser).
			if (!browser) return;

			if (response.status !== 401) return;

			// Don't refresh on auth endpoints or already-retried requests.
			const url = new URL(request.url);
			if (url.pathname.startsWith('/auth/') || request.headers.has(RETRY_HEADER)) return;

			// Get the cloned request for replay.
			const originalRequest = clones.get(request);
			clones.delete(request);
			if (!originalRequest) return;

			const FnFetch = options.fetch;

			// Deduplicate: if a refresh is already in progress, wait for it.
			if (!refreshPromise) {
				refreshPromise = refreshAccessToken(FnFetch).finally(() => {
					refreshPromise = null;
				});
			}
			const refreshSucceeded = await refreshPromise;

			if (!refreshSucceeded) {
				return response; // Refresh failed — return the original 401
			}

			// Replay the original request. Browser cookie jar already has new tokens.
			const retryHeaders = new Headers(originalRequest.headers);
			retryHeaders.set(RETRY_HEADER, '1');

			return FnFetch(
				new Request(originalRequest, {
					headers: retryHeaders
				})
			);
		}
	};
}
