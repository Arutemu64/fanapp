import { PRIVATE_API_URL } from '$env/static/private';
import { PUBLIC_API_URL } from '$env/static/public';
import { client } from '$lib/api';
import type { Handle, HandleFetch } from '@sveltejs/kit';
import { redirect } from '@sveltejs/kit';
import * as setCookieParser from 'set-cookie-parser';

const protectedRoutes = ['/profile'];

export const handleFetch: HandleFetch = async ({ request, fetch, event }) => {
	// https://svelte.dev/docs/kit/hooks#Server-hooks-handleFetch
	if (request.url.startsWith(PUBLIC_API_URL)) {
		// Replace public API with private URL for server-side requests
		request = new Request(request.url.replace(PUBLIC_API_URL, PRIVATE_API_URL), request);
	}
	if (request.url.startsWith(PRIVATE_API_URL)) {
		// Forward browser cookies with server-side API requests, 
		// but avoid overwriting explicitly set cookies (e.g. from token refresh retries)
		if (!request.headers.has('cookie')) {
			request.headers.set('cookie', event.request.headers.get('cookie') || '');
		}
	}
	return fetch(request);
};

export const handle: Handle = async ({ event, resolve }) => {
	// Load user
	const { data, error, response: apiResponse } = await client.GET('/users/me', { fetch: event.fetch });
	if (data && !error) {
		event.locals.user = data;
	} else {
		event.locals.user = null;
	}

	// Propagate new cookies from the API to the browser if they were refreshed
	if (apiResponse && apiResponse.headers.has('set-cookie')) {
		const cookies = apiResponse.headers.getSetCookie();
		const parsedCookies = setCookieParser.parse(cookies);

		for (const cookie of parsedCookies) {
			const { name, value, ...options } = cookie;
			event.cookies.set(name, value, {
				path: '/', // SvelteKit requires path to be strictly defined
				...options,
				// ensure samesite matches SvelteKit's expected union type
				sameSite: options.sameSite as 'strict' | 'lax' | 'none' | undefined
			});
		}
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
