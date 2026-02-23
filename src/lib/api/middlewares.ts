import { PUBLIC_API_URL } from '$env/static/public';
import type { Middleware } from 'openapi-fetch';

async function refreshAccessToken(FnFetch: typeof fetch): Promise<Response | null> {
	try {
		const response = await FnFetch(`${PUBLIC_API_URL}/auth/refresh`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json'
			}
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

export const refreshTokenMiddleware: Middleware = {
	async onRequest({ request, options }) {
		const FnFetch = options.fetch;
		const duplicate = request.clone();
		const response = await FnFetch(request);

		if (response.status !== 401) {
			return response;
		}

		const refreshResponse = await refreshAccessToken(FnFetch);

		if (!refreshResponse) {
			return response; // Return the 401 response
		}

		// Extract cookies from refresh response
		const setCookieHeaders = refreshResponse.headers.getSetCookie();
		const cookieHeader = setCookieHeaders.map((setCookie) => setCookie.split(';')[0]).join('; ');

		// Add cookies to the retry request
		const retryHeaders = new Headers(duplicate.headers);
		if (cookieHeader) {
			retryHeaders.set('Cookie', cookieHeader);
		}

		// Retry the original request with new cookies
		const retryResponse = await FnFetch(duplicate.url, {
			method: duplicate.method,
			headers: retryHeaders,
			body: duplicate.body,
			credentials: duplicate.credentials
		});

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
