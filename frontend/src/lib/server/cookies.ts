import type { Cookies } from '@sveltejs/kit';
import setCookieParser from 'set-cookie-parser';

type ParsedCookie = setCookieParser.Cookie;

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
		cookies.set(cookie.name, cookie.value, {
			path: cookie.path ?? '/',
			httpOnly: cookie.httpOnly ?? true,
			secure: cookie.secure ?? false,
			sameSite: (cookie.sameSite as 'lax' | 'strict' | 'none') ?? 'lax',
			maxAge: cookie.maxAge
		});
	}
}

/**
 * Rebuild the `cookie` header on a Request so that subsequent
 * server-side fetches (via `event.fetch`) use the fresh tokens.
 */
export function updateRequestCookieHeader(request: Request, parsed: ParsedCookie[]): void {
	const updatedNames = new Set(parsed.map((c) => c.name));
	const preserved = (request.headers.get('cookie') ?? '')
		.split(';')
		.map((c) => c.trim())
		.filter((c) => !updatedNames.has(c.split('=')[0] ?? ''));
	const fresh = parsed.map((c) => `${c.name}=${c.value}`);

	request.headers.set('cookie', [...preserved, ...fresh].join('; '));
}
