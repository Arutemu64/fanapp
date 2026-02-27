import { PUBLIC_API_URL } from '$env/static/public';
import type { Middleware } from 'openapi-fetch';

async function refreshAccessToken(FnFetch: typeof fetch): Promise<Response | null> {
	try {
		const response = await FnFetch(`${PUBLIC_API_URL}/auth/refresh`, {
			method: 'POST',
			credentials: 'include'
		});

		if (!response.ok) {
			return null;
		}

		return response;
	} catch (error) {
		console.error('Failed to refresh token:', error);
		return null;
	}
}

export function createRefreshTokenMiddleware(): Middleware {
	const clones = new WeakMap<Request, Request>();
	let refreshPromise: Promise<Response | null> | null = null;

	return {
		onRequest({ request }) {
			// Clone BEFORE the body stream is consumed by fetch
			clones.set(request, request.clone());
		},

		async onResponse({ request, response, options }) {
			if (response.status !== 401) return;

			// Skip refresh for auth endpoints to avoid wasted calls
			if (request.url.includes('/auth/')) return;

			const originalRequest = clones.get(request);
			clones.delete(request);
			if (!originalRequest) return response;

			const FnFetch = options.fetch;

			// Deduplicate concurrent refresh attempts
			if (!refreshPromise) {
				refreshPromise = refreshAccessToken(FnFetch).finally(() => {
					refreshPromise = null;
				});
			}
			const refreshResponse = await refreshPromise;

			if (!refreshResponse) {
				return response; // Return the original 401 response
			}

			// Extract cookies from refresh response
			const setCookieHeaders = refreshResponse.headers.getSetCookie();
			const cookieHeader = setCookieHeaders.map((setCookie) => setCookie.split(';')[0]).join('; ');

			// Add cookies to the retry request
			const retryHeaders = new Headers(originalRequest.headers);
			if (cookieHeader) {
				retryHeaders.set('Cookie', cookieHeader);
			}

			// Retry the original request with new cookies
			const retryResponse = await FnFetch(
				new Request(originalRequest, {
					headers: retryHeaders
				})
			);

			// Propagate Set-Cookie headers from refresh response to the final response
			if (setCookieHeaders.length > 0) {
				const newHeaders = new Headers(retryResponse.headers);
				for (const setCookie of setCookieHeaders) {
					newHeaders.append('Set-Cookie', setCookie);
				}
				return new Response(retryResponse.body, {
					status: retryResponse.status,
					statusText: retryResponse.statusText,
					headers: newHeaders
				});
			}

			return retryResponse;
		}
	};
}
