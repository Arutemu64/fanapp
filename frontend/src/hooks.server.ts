import * as Sentry from '@sentry/sveltekit';
import { env as privateEnv } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';

const { PRIVATE_API_URL } = privateEnv;
const { PUBLIC_API_URL } = publicEnv;

// These come from the runtime environment ($env/dynamic), so the types are
// `string | undefined`. The server cannot proxy API requests without them, so
// fail fast at startup instead of crashing later on a confusing `undefined`.
if (!PUBLIC_API_URL || !PRIVATE_API_URL) {
	throw new Error('PUBLIC_API_URL and PRIVATE_API_URL environment variables must be set');
}

import { createApiClient } from '$lib/api';
import {
	applyResponseCookies,
	clearAuthCookies,
	setRequestCookiesHeader
} from '$lib/server/cookies';
import type { UserFullDTO } from '$lib/types/user';
import type { Handle, HandleFetch, HandleServerError, RequestEvent } from '@sveltejs/kit';
import { redirect } from '@sveltejs/kit';
import { sequence } from '@sveltejs/kit/hooks';

// Route-group folders that drive access control. SvelteKit puts the group name
// (in parentheses) into the route id, so we can detect them with a substring.
const PROTECTED_GROUP = '(protected)'; // requires a logged-in user
const GUEST_ONLY_GROUP = '(auth)'; // login/register pages — only for guests

const LOGIN_PATH = '/login';
const HOME_PATH = '/';

// Trim a trailing slash so we can append our own and match on a clean boundary.
const PUBLIC_API_BASE = PUBLIC_API_URL.replace(/\/$/, '');
const PRIVATE_API_BASE = PRIVATE_API_URL.replace(/\/$/, '');

/**
 * Match a URL against an API base, requiring a path boundary.
 *
 * Using `startsWith(base + '/')` (instead of a bare `startsWith(base)`) stops a
 * malicious host like `https://api.example.com.evil.com` from matching
 * `https://api.example.com`.
 */
function isApiUrl(url: string, base: string): boolean {
	return url === base || url.startsWith(`${base}/`);
}

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
	// Server-side SSR fetches go to the public URL; rewrite them to the internal
	// (in-cluster) URL so they never leave the network.
	if (isApiUrl(request.url, PUBLIC_API_BASE)) {
		const internalUrl = PRIVATE_API_BASE + request.url.slice(PUBLIC_API_BASE.length);
		// Clone the original request, but change the URL (official SvelteKit pattern).
		request = new Request(internalUrl, request);
	}

	const isInternalApi = isApiUrl(request.url, PRIVATE_API_BASE);

	if (isInternalApi) {
		// Keep internal SSR fetches in sync with cookies that were changed earlier
		// in the same request, such as login, logout, or session refresh.
		setRequestCookiesHeader(request, event.cookies);
	}

	const response = await fetch(request);

	if (isInternalApi) {
		// Mirror backend Set-Cookie headers into SvelteKit's cookie store so the
		// browser receives them in the final SSR response.
		applyResponseCookies(event.cookies, response);
	}

	return response;
};

/**
 * Fetch the current user from the backend. Returns `null` for any "not logged
 * in" situation so callers never have to handle errors.
 */
async function loadCurrentUser(event: RequestEvent): Promise<UserFullDTO | null> {
	try {
		const client = createApiClient();
		const result = await client.GET('/me/', { fetch: event.fetch });

		// Stale or invalid session — drop the cookie so the user becomes a guest.
		if (result.response.status === 401 || result.response.status === 403) {
			clearAuthCookies(event.cookies);
			return null;
		}

		return result.data && !result.error ? result.data : null;
	} catch {
		// Backend unreachable (network error / timeout). Render the page as a guest
		// instead of failing the whole request with a 500.
		return null;
	}
}

/**
 * Load the current user into `event.locals` and tag Sentry, so every later hook,
 * load function, and page can read `locals.user`.
 */
const authHandle: Handle = async ({ event, resolve }) => {
	const sessionId = event.cookies.get('session_id');
	event.locals.user = sessionId ? await loadCurrentUser(event) : null;

	if (event.locals.user) {
		Sentry.setUser({ id: event.locals.user.id, username: event.locals.user.username ?? undefined });
	} else {
		Sentry.setUser(null);
	}

	return resolve(event);
};

/**
 * Enforce route-group access rules based on the user loaded in `authHandle`.
 */
const guardHandle: Handle = async ({ event, resolve }) => {
	const routeId = event.route.id;

	// Protected pages need a user; send guests to login.
	if (routeId?.includes(PROTECTED_GROUP) && !event.locals.user) {
		redirect(303, LOGIN_PATH);
	}

	// Guest-only pages (login/register) make no sense for a logged-in user.
	if (routeId?.includes(GUEST_ONLY_GROUP) && event.locals.user) {
		redirect(303, HOME_PATH);
	}

	return resolve(event, {
		filterSerializedResponseHeaders: (name) => name === 'content-length'
	});
};

// Order matters: Sentry first, then load the user, then guard routes with it.
export const handle: Handle = sequence(Sentry.sentryHandle(), authHandle, guardHandle);

export const handleError: HandleServerError = Sentry.handleErrorWithSentry(({ error }) => {
	const err = error as { code?: string } | undefined;

	// Localized Russian error response to fulfill the Russian Copy policy
	return {
		message: 'Произошла непредвиденная ошибка на сервере.',
		code: err?.code ?? 'UNKNOWN'
	};
});
