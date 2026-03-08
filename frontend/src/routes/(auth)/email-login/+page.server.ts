import { PUBLIC_API_URL } from '$env/static/public';
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import * as setCookieParser from 'set-cookie-parser';

const INVALID_LINK_MESSAGE = 'Ссылка для входа недействительна или уже устарела.';

function extractSetCookieHeaders(response: Response): string[] {
	const directHeaders = response.headers.getSetCookie();
	if (directHeaders.length > 0) {
		return directHeaders;
	}

	const combinedHeader = response.headers.get('set-cookie');
	return combinedHeader ? setCookieParser.splitCookiesString(combinedHeader) : [];
}

function applyResponseCookies(
	cookies: Parameters<PageServerLoad>[0]['cookies'],
	responseCookies: string[]
) {
	for (const cookie of setCookieParser.parse(responseCookies)) {
		const { name, value, ...options } = cookie;
		cookies.set(name, value, {
			path: options.path ?? '/',
			...options,
			sameSite: options.sameSite as 'strict' | 'lax' | 'none' | undefined
		});
	}
}

export const load: PageServerLoad = async ({ fetch, url, cookies }) => {
	const token = url.searchParams.get('token');

	if (!token) {
		return {
			errorMessage: 'Ссылка для входа не содержит токен.'
		};
	}

	const response = await fetch(`${PUBLIC_API_URL}/auth/login-magic-link`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({ token })
	});

	const responseCookies = extractSetCookieHeaders(response);
	if (responseCookies.length > 0) {
		applyResponseCookies(cookies, responseCookies);
	}

	if (!response.ok) {
		console.error('Magic link login error:', response.status, response.statusText);
		return {
			errorMessage: INVALID_LINK_MESSAGE
		};
	}

	redirect(303, '/');
};
