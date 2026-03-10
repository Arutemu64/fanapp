import { PRIVATE_API_URL } from '$env/static/private';
import { PUBLIC_API_URL } from '$env/static/public';
import { createApiClient } from '$lib/api';
import {
	applyResponseCookies,
	parseResponseCookies,
	updateRequestCookieHeader
} from '$lib/server/cookies';
import type { Handle, HandleFetch, RequestEvent } from '@sveltejs/kit';
import { error, redirect } from '@sveltejs/kit';

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
	// Replace public API with private API
	if (request.url.startsWith(PUBLIC_API_URL)) {
		request = new Request(request.url.replace(PUBLIC_API_URL, PRIVATE_API_URL), request);
	}
	// Pass cookies from the incoming browser request (or updated by previous fetches)
	const cookieHeader = event.request.headers.get('cookie');
	if (cookieHeader) {
		request.headers.set('cookie', cookieHeader);
	}

	const response = await fetch(request);

	// Automatically forward any Set-Cookie headers from API → browser
	const parsed = parseResponseCookies(response);
	if (parsed.length > 0) {
		applyResponseCookies(event.cookies, parsed);
		updateRequestCookieHeader(event.request, parsed);
	}

	return response;
};

/**
 * Attempt to refresh auth tokens server-side.
 * Cookie forwarding is handled automatically by handleFetch.
 *
 * Returns true if refresh succeeded.
 */
async function refreshTokens(event: RequestEvent): Promise<boolean> {
	const refreshResponse = await event.fetch(`${PUBLIC_API_URL}/auth/refresh`, {
		method: 'POST'
		// handleFetch will rewrite URL, forward cookies, and apply Set-Cookie headers
	});

	return refreshResponse.ok;
}

export const handle: Handle = async ({ event, resolve }) => {
	const routeId = event.route.id;
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

	if (routeId?.includes('(protected)')) {
		if (!event.locals.user) {
			throw redirect(303, '/login');
		}
	}

	// Block the whole organizer area server-side so every nested org page stays protected.
	if (routeId?.includes('(protected)/org') && event.locals.user?.role !== 'org') {
		throw error(403, 'У вас нет доступа к разделу организаторов');
	}

	if (routeId?.includes('(auth)')) {
		if (event.locals.user) {
			throw redirect(303, '/');
		}
	}

	return resolve(event, {
		filterSerializedResponseHeaders: (name) => name === 'content-length'
	});
};
