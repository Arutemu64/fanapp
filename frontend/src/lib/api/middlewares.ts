import { browser } from '$app/environment';
import { PUBLIC_API_URL } from '$env/static/public';
import type { Middleware } from 'openapi-fetch';

const RETRY_HEADER = 'x-auth-refresh-retry';

async function refreshAccessToken(FnFetch: typeof fetch): Promise<boolean> {
	try {
		const response = await FnFetch(`${PUBLIC_API_URL}/auth/refresh`, {
			method: 'POST',
			credentials: 'include'
		});

		return response.ok;
	} catch (error) {
		console.error('Failed to refresh token:', error);
		return false;
	}
}

export function createRefreshTokenMiddleware(): Middleware {
	const clones = new WeakMap<Request, Request>();
	let refreshPromise: Promise<boolean> | null = null;

	return {
		onRequest({ request }) {
			if (!browser) return;
			// Browser retries need a fresh Request instance because fetch bodies are single-use.
			clones.set(request, request.clone());
		},

		async onResponse({ request, response, options }) {
			if (!browser) return;
			if (response.status !== 401) return;

			// Skip auth endpoints and already retried requests to avoid refresh loops.
			if (request.url.includes('/auth/') || request.headers.has(RETRY_HEADER)) return;

			const originalRequest = clones.get(request);
			clones.delete(request);
			if (!originalRequest) return response;

			const FnFetch = options.fetch;

			// Deduplicate concurrent refresh attempts
			if (!refreshPromise) {
				// Collapse multiple simultaneous 401s in the browser into one refresh call.
				refreshPromise = refreshAccessToken(FnFetch).finally(() => {
					refreshPromise = null;
				});
			}
			const refreshSucceeded = await refreshPromise;

			if (!refreshSucceeded) {
				return response; // Return the original 401 response
			}

			// The browser owns the cookie jar here, so a plain retry is enough after refresh.
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
