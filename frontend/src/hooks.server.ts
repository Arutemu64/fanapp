import { PRIVATE_API_URL } from '$env/static/private';
import { PUBLIC_API_URL } from '$env/static/public';
import { createApiClient } from '$lib/api';
import type { Handle, HandleFetch } from '@sveltejs/kit';
import { redirect } from '@sveltejs/kit';
import * as setCookieParser from 'set-cookie-parser';

const RETRY_HEADER = 'x-auth-refresh-retry';
const REFRESH_PROMISE_KEY = '__authRefreshPromise';

function serializeEventCookies(event: Parameters<HandleFetch>[0]['event']): string {
	return event.cookies
		.getAll()
		.map(({ name, value }) => `${name}=${value}`)
		.join('; ');
}

function withCookieHeader(request: Request, cookieHeader: string): Request {
	if (!cookieHeader) return request;

	const headers = new Headers(request.headers);
	headers.set('cookie', cookieHeader);

	return new Request(request, {
		headers
	});
}

function applySetCookieHeaders(event: Parameters<HandleFetch>[0]['event'], cookies: string[]) {
	// Mirror API-issued Set-Cookie headers into SvelteKit's cookie jar so:
	// 1) the retried SSR request sees fresh cookies immediately, and
	// 2) the browser receives the updated cookies in the final response.
	const parsedCookies = setCookieParser.parse(cookies);

	for (const cookie of parsedCookies) {
		const { name, value, ...options } = cookie;
		event.cookies.set(name, value, {
			path: options.path ?? '/',
			...options,
			sameSite: options.sameSite as 'strict' | 'lax' | 'none' | undefined
		});
	}
}

async function refreshServerAuth(event: Parameters<HandleFetch>[0]['event'], fetch: typeof globalThis.fetch) {
	const locals = event.locals as typeof event.locals & {
		[REFRESH_PROMISE_KEY]?: Promise<Response | null> | null;
	};

	if (!locals[REFRESH_PROMISE_KEY]) {
		// Deduplicate concurrent SSR refreshes within the same page request.
		locals[REFRESH_PROMISE_KEY] = fetch(
			withCookieHeader(
				new Request(`${PRIVATE_API_URL}/auth/refresh`, {
					method: 'POST'
				}),
				serializeEventCookies(event)
			)
		)
			.then((response) => (response.ok ? response : null))
			.catch((error) => {
				console.error('Failed to refresh token:', error);
				return null;
			})
			.finally(() => {
				locals[REFRESH_PROMISE_KEY] = null;
			});
	}

	return locals[REFRESH_PROMISE_KEY];
}

export const handleFetch: HandleFetch = async ({ request, fetch, event }) => {
	const isApiRequest =
		request.url.startsWith(PUBLIC_API_URL) || request.url.startsWith(PRIVATE_API_URL);
	const isRetryAttempt = request.headers.has(RETRY_HEADER);

	if (request.url.startsWith(PUBLIC_API_URL)) {
		// Replace public API with private URL for server-side requests
		request = new Request(request.url.replace(PUBLIC_API_URL, PRIVATE_API_URL), request);
	}

	if (request.url.startsWith(PRIVATE_API_URL)) {
		// Strip the internal retry marker before the request reaches the backend.
		const headers = new Headers(request.headers);
		headers.delete(RETRY_HEADER);

		request = new Request(request, { headers });

		if (!request.headers.has('cookie')) {
			// Always build the outgoing SSR cookie header from event.cookies so retries
			// pick up freshly refreshed values written during this request.
			request = withCookieHeader(request, serializeEventCookies(event));
		}
	}

	const response = await fetch(request);
	if (
		!isApiRequest ||
		!request.url.startsWith(PRIVATE_API_URL) ||
		response.status !== 401 ||
		request.url.includes('/auth/') ||
		isRetryAttempt
	) {
		return response;
	}

	const refreshResponse = await refreshServerAuth(event, fetch);
	if (!refreshResponse) {
		return response;
	}

	const setCookieHeaders = refreshResponse.headers.getSetCookie();
	if (setCookieHeaders.length > 0) {
		applySetCookieHeaders(event, setCookieHeaders);
	}

	// Retry once with the refreshed per-request cookie jar.
	const retryHeaders = new Headers(request.headers);
	retryHeaders.set(RETRY_HEADER, '1');

	return fetch(
		withCookieHeader(
			new Request(request, {
				headers: retryHeaders
			}),
			serializeEventCookies(event)
		)
	);
};

export const handle: Handle = async ({ event, resolve }) => {
	// Create a per-request client to avoid cross-request state leakage
	const serverClient = createApiClient();

	// Load user
	const {
		data,
		error
	} = await serverClient.GET('/users/me', { fetch: event.fetch });
	if (data && !error) {
		event.locals.user = data;
	} else {
		event.locals.user = null;
	}

	// Protect routes based on the directory group
	if (event.route.id?.includes('(protected)')) {
		if (!event.locals.user) {
			throw redirect(303, '/login');
		}
	}

	// Prevent authenticated users from accessing auth routes
	if (event.route.id?.includes('(auth)')) {
		if (event.locals.user) {
			throw redirect(303, '/');
		}
	}

	// Include content-length and any other custom headers your API uses
	return resolve(event, {
		filterSerializedResponseHeaders: (name) => name === 'content-length'
	});
};
