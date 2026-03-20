import type { Cookies } from '@sveltejs/kit';
import type { Cookie } from 'set-cookie-parser';
import setCookieParser from 'set-cookie-parser';

type ParsedCookie = Cookie;

// Keep auth cookie names in one place so hooks and server routes stay consistent.
export const AUTH_COOKIE_NAMES = ['access_token', 'refresh_token'] as const;

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
 * Parse Set-Cookie headers from a fetch Response into structured objects.
 */
export function parseResponseCookies(response: Response): ParsedCookie[] {
	return setCookieParser.parse(
		setCookieParser.splitCookiesString(response.headers.get('set-cookie') ?? '')
	);
}

/**
 * Apply parsed cookies to the SvelteKit `cookies` object
 * so they are forwarded to the browser in the SSR response.
 */
export function applyResponseCookies(cookies: Cookies, parsed: ParsedCookie[]): void {
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
