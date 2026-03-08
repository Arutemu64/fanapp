import { PRIVATE_API_URL } from '$env/static/private';
import { PUBLIC_API_URL } from '$env/static/public';
import { createApiClient } from '$lib/api';
import type { Handle, HandleFetch } from '@sveltejs/kit';
import { redirect } from '@sveltejs/kit';
import * as setCookieParser from 'set-cookie-parser';

// Header used to prevent infinite retry loops (401 → refresh → 401 → ...).
const RETRY_HEADER = 'x-auth-refresh-retry';

// ---------------------------------------------------------------------------
// Cookie helpers for SSR
// ---------------------------------------------------------------------------

/**
 * Serialize all cookies from the SvelteKit event into a single Cookie header string.
 * Needed because server-side fetch doesn't automatically include cookies.
 */
function serializeEventCookies(event: Parameters<HandleFetch>[0]['event']): string {
	return event.cookies
		.getAll()
		.map(({ name, value }) => `${name}=${value}`)
		.join('; ');
}

/**
 * Clone a Request with a specific Cookie header attached.
 */
function withCookieHeader(request: Request, cookieHeader: string): Request {
	if (!cookieHeader) return request;
	const headers = new Headers(request.headers);
	headers.set('cookie', cookieHeader);
	return new Request(request, { headers });
}

/**
 * Mirror Set-Cookie headers from the API response into SvelteKit's cookie jar.
 * This ensures:
 *   1. Subsequent SSR fetches in the same request see the fresh cookies.
 *   2. The browser receives the updated cookies in the final HTML response.
 */
function applySetCookieHeaders(event: Parameters<HandleFetch>[0]['event'], cookies: string[]) {
	for (const cookie of setCookieParser.parse(cookies)) {
		const { name, value, ...options } = cookie;
		event.cookies.set(name, value, {
			path: options.path ?? '/',
			...options,
			sameSite: options.sameSite as 'strict' | 'lax' | 'none' | undefined
		});
	}
}

// ---------------------------------------------------------------------------
// SSR token refresh
// ---------------------------------------------------------------------------

// We store the in-flight refresh promise on event.locals to deduplicate
// concurrent refreshes within the same page request.
const REFRESH_PROMISE_KEY = '__authRefreshPromise';

/**
 * Call POST /auth/refresh on the backend. Returns the Response if successful, null otherwise.
 * Concurrent calls during the same SSR request are collapsed into a single fetch.
 */
async function refreshServerAuth(event: Parameters<HandleFetch>[0]['event']) {
	const locals = event.locals as typeof event.locals & {
		[REFRESH_PROMISE_KEY]?: Promise<Response | null> | null;
	};

	if (!locals[REFRESH_PROMISE_KEY]) {
		// Use event.fetch so the refresh request keeps the original SSR request context.
		// This is important for cookies and other request-bound behavior during reloads.
		locals[REFRESH_PROMISE_KEY] = event
			.fetch(`${PUBLIC_API_URL}/auth/refresh`, { method: 'POST' })
			.then((r) => (r.ok ? r : null))
			.catch((err) => {
				console.error('Failed to refresh token:', err);
				return null;
			})
			.finally(() => {
				locals[REFRESH_PROMISE_KEY] = null;
			});
	}

	return locals[REFRESH_PROMISE_KEY];
}

// ---------------------------------------------------------------------------
// handleFetch — intercept every server-side fetch
// ---------------------------------------------------------------------------

export const handleFetch: HandleFetch = async ({ request, fetch, event }) => {
	const isApiRequest =
		request.url.startsWith(PUBLIC_API_URL) || request.url.startsWith(PRIVATE_API_URL);
	const isRetryAttempt = request.headers.has(RETRY_HEADER);

	// For internal API requests: attach cookies and strip retry marker.
	if (request.url.startsWith(PRIVATE_API_URL)) {
		const headers = new Headers(request.headers);
		headers.delete(RETRY_HEADER);
		request = new Request(request, { headers });

		// Always build cookie header from event.cookies so retries pick up
		// freshly refreshed values written during this request.
		if (!request.headers.has('cookie')) {
			request = withCookieHeader(request, serializeEventCookies(event));
		}
	}

	// Execute the actual fetch.
	const response = await fetch(request);

	// Mirror auth cookies from any SSR API response, not just /auth/refresh.
	// This is required for flows like magic-link login that set cookies during a server load.
	if (request.url.startsWith(PRIVATE_API_URL)) {
		const setCookieHeaders = response.headers.getSetCookie();
		if (setCookieHeaders.length > 0) {
			applySetCookieHeaders(event, setCookieHeaders);
		}
	}

	// If it's not a 401 from an API call, or it's an auth endpoint, or it's already
	// a retry — return as-is.
	const url = new URL(request.url);
	if (
		!isApiRequest ||
		response.status !== 401 ||
		url.pathname.startsWith('/auth/') ||
		isRetryAttempt
	) {
		return response;
	}

	// Got a 401 — try to refresh the access token.
	const refreshResponse = await refreshServerAuth(event);
	if (!refreshResponse) {
		return response; // Refresh failed — return original 401
	}

	// Retry the original request with the new cookies (once only).
	const retryHeaders = new Headers(request.headers);
	retryHeaders.set(RETRY_HEADER, '1');

	return fetch(
		withCookieHeader(new Request(request, { headers: retryHeaders }), serializeEventCookies(event))
	);
};

// ---------------------------------------------------------------------------
// handle — runs on every incoming request
// ---------------------------------------------------------------------------

export const handle: Handle = async ({ event, resolve }) => {
	// Load the current user when we have any auth cookie.
	// This keeps SSR page refresh working even after the short-lived access token
	// expires, because the first /users/me request can trigger refresh via the
	// still-valid refresh_token cookie inside handleFetch.
	const hasToken = event.cookies.get('access_token') || event.cookies.get('refresh_token');

	if (hasToken) {
		const serverClient = createApiClient();
		const { data, error } = await serverClient.GET('/users/me', { fetch: event.fetch });
		event.locals.user = data && !error ? data : null;
	} else {
		event.locals.user = null;
	}

	// Route guards based on directory groups in the routes folder.
	if (event.route.id?.includes('(protected)')) {
		if (!event.locals.user) {
			throw redirect(303, '/login');
		}
	}

	if (event.route.id?.includes('(auth)')) {
		if (event.locals.user) {
			throw redirect(303, '/');
		}
	}

	return resolve(event, {
		filterSerializedResponseHeaders: (name) => name === 'content-length'
	});
};
