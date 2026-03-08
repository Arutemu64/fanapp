import { PRIVATE_API_URL } from '$env/static/private';
import { PUBLIC_API_URL } from '$env/static/public';
import { createApiClient } from '$lib/api';
import {
	applyResponseCookies,
	parseResponseCookies,
	updateRequestCookieHeader
} from '$lib/server/cookies';
import type { Handle, HandleFetch, RequestEvent } from '@sveltejs/kit';
import { redirect } from '@sveltejs/kit';

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
	// Replace public API with private API
	if (request.url.startsWith(PUBLIC_API_URL)) {
		request = new Request(request.url.replace(PUBLIC_API_URL, PRIVATE_API_URL), request);
	}
	// Pass cookies from the incoming browser request (or updated by refreshTokens)
	const cookieHeader = event.request.headers.get('cookie');
	if (cookieHeader) {
		request.headers.set('cookie', cookieHeader);
	}

	return fetch(request);
};

/**
 * Attempt to refresh auth tokens server-side.
 *
 * On success:
 *   1. Parses set-cookie headers from the API response
 *   2. Updates event.cookies (→ browser gets new tokens in the SSR response)
 *   3. Updates event.request cookie header (→ subsequent event.fetch calls use new tokens)
 *
 * Returns true if refresh succeeded.
 */
async function refreshTokens(event: RequestEvent): Promise<boolean> {
	const refreshResponse = await event.fetch(`${PUBLIC_API_URL}/auth/refresh`, {
		method: 'POST'
		// handleFetch will rewrite URL to PRIVATE_API_URL and forward cookies
	});

	if (!refreshResponse.ok) return false;

	const parsed = parseResponseCookies(refreshResponse);
	applyResponseCookies(event.cookies, parsed);
	updateRequestCookieHeader(event.request, parsed);

	return true;
}

export const handle: Handle = async ({ event, resolve }) => {
	const hasToken = event.cookies.get('access_token') || event.cookies.get('refresh_token');

	if (hasToken) {
		const client = createApiClient();
		let { data, error, response } = await client.GET('/users/me', { fetch: event.fetch });

		// If access_token expired but refresh_token is still valid, refresh server-side
		if (response.status === 401 && event.cookies.get('refresh_token')) {
			const refreshed = await refreshTokens(event);
			if (refreshed) {
				({ data, error } = await client.GET('/users/me', { fetch: event.fetch }));
			}
		}

		event.locals.user = data && !error ? data : null;
	} else {
		event.locals.user = null;
	}

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
