import { PRIVATE_API_URL } from '$env/static/private';
import { PUBLIC_API_URL } from '$env/static/public';
import { createApiClient } from '$lib/api';
import {
	applyResponseCookies,
	clearAuthCookies,
	parseResponseCookies,
	serializeRequestCookies
} from '$lib/server/cookies';
import type { Handle, HandleFetch, RequestEvent } from '@sveltejs/kit';
import { error, redirect } from '@sveltejs/kit';

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
	// Replace public API with private API
	if (request.url.startsWith(PUBLIC_API_URL)) {
		request = new Request(request.url.replace(PUBLIC_API_URL, PRIVATE_API_URL), request);
	}

	const isInternalApi = request.url.startsWith(PRIVATE_API_URL);

	if (isInternalApi) {
		// Rebuild cookies from SvelteKit's cookie store so server-side refreshes or
		// deletions earlier in the same request are visible to later API calls.
		const cookieHeader = serializeRequestCookies(event.cookies);
		if (cookieHeader) {
			request.headers.set('cookie', cookieHeader);
		} else {
			request.headers.delete('cookie');
		}
	}

	const response = await fetch(request);

	if (isInternalApi) {
		// Automatically forward any Set-Cookie headers from API → browser
		const parsed = parseResponseCookies(response);
		if (parsed.length > 0) {
			applyResponseCookies(event.cookies, parsed);
		}
	}

	return response;
};

async function loadCurrentUser(event: RequestEvent) {
	const client = createApiClient();
	const result = await client.GET('/me/', { fetch: event.fetch });

	if (result.response.status === 401 || result.response.status === 403) {
		clearAuthCookies(event.cookies);
		return null;
	}

	return result.data && !result.error ? result.data : null;
}

export const handle: Handle = async ({ event, resolve }) => {
	const routeId = event.route.id;
	const hasToken = event.cookies.get('session_id');

	if (hasToken) {
		event.locals.user = await loadCurrentUser(event);
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
