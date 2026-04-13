import type { Cookies } from '@sveltejs/kit';
import type { Cookie } from 'set-cookie-parser';
import setCookieParser from 'set-cookie-parser';

type ParsedCookie = Cookie;

// Keep auth cookie names in one place so hooks and server routes stay consistent.
export const AUTH_COOKIE_NAMES = ['session_id'] as const;

type HeadersWithGetSetCookie = Headers & {
	getSetCookie?: () => string[];
};

/**
 * Convert SvelteKit's request cookie store back into a Cookie header.
 *
 * We rebuild the header from `event.cookies` instead of mutating `event.request`.
 * That keeps later server-side fetches in sync with any cookies that were set or
 * deleted earlier in the same request.
 */
export function serializeRequestCookies(cookies: Cookies): string {
	return cookies
		.getAll()
		.map(({ name, value }) => `${name}=${value}`)
		.join('; ');
}

/**
 * Write the current request-aware cookies into an outgoing server fetch.
 *
 * This keeps SSR fetches in sync with cookie changes that happened earlier in
 * the same request, such as login, logout, or session renewal.
 */
export function setRequestCookiesHeader(request: Request, cookies: Cookies): void {
	const cookieHeader = serializeRequestCookies(cookies);

	if (cookieHeader) {
		request.headers.set('cookie', cookieHeader);
		return;
	}

	request.headers.delete('cookie');
}

/**
 * Clear auth cookies from the current SvelteKit response and request context.
 */
export function clearAuthCookies(cookies: Cookies): void {
	for (const cookieName of AUTH_COOKIE_NAMES) {
		cookies.delete(cookieName, { path: '/' });
	}
}

function getSameSiteValue(cookie: ParsedCookie): 'lax' | 'strict' | 'none' | undefined {
	if (typeof cookie.sameSite !== 'string') {
		return undefined;
	}

	const normalized = cookie.sameSite.toLowerCase();

	if (normalized === 'lax' || normalized === 'strict' || normalized === 'none') {
		return normalized;
	}

	return undefined;
}

/**
 * Read every Set-Cookie header from a Response.
 *
 * Newer runtimes expose `headers.getSetCookie()`. We prefer that when it is
 * available and fall back to the combined `set-cookie` header for compatibility.
 */
function getSetCookieHeaders(headers: Headers): string[] {
	const headersWithGetSetCookie = headers as HeadersWithGetSetCookie;

	if (typeof headersWithGetSetCookie.getSetCookie === 'function') {
		return headersWithGetSetCookie.getSetCookie();
	}

	const combinedHeader = headers.get('set-cookie');
	if (!combinedHeader) {
		return [];
	}

	return setCookieParser.splitCookiesString(combinedHeader);
}

/**
 * Copy backend Set-Cookie headers into SvelteKit's cookie store so they are
 * forwarded to the browser in the final SSR response.
 */
export function applyResponseCookies(cookies: Cookies, response: Response): void {
	const parsed = setCookieParser.parse(getSetCookieHeaders(response.headers));

	for (const cookie of parsed) {
		// Start with SvelteKit's safe defaults and only copy attributes that the
		// backend actually sent. This avoids accidentally weakening cookie security.
		const options: Parameters<Cookies['set']>[2] = {
			path: cookie.path ?? '/'
		};

		if (cookie.domain) {
			options.domain = cookie.domain;
		}

		if (cookie.expires) {
			options.expires = cookie.expires;
		}

		if (cookie.httpOnly !== undefined) {
			options.httpOnly = cookie.httpOnly;
		}

		if (cookie.maxAge !== undefined) {
			options.maxAge = cookie.maxAge;
		}

		if (cookie.secure !== undefined) {
			options.secure = cookie.secure;
		}

		const sameSite = getSameSiteValue(cookie);
		if (sameSite) {
			options.sameSite = sameSite;
		}

		cookies.set(cookie.name, cookie.value, options);
	}
}
