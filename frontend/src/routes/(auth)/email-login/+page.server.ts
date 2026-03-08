import { createApiClient } from '$lib/api';
import { applyResponseCookies, parseResponseCookies } from '$lib/server/cookies';
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const INVALID_LINK_MESSAGE = 'Ссылка для входа недействительна или уже устарела.';

export const load: PageServerLoad = async ({ fetch, url, cookies }) => {
	const token = url.searchParams.get('token');

	if (!token) {
		return {
			errorMessage: 'Ссылка для входа не содержит токен.'
		};
	}

	const client = createApiClient();
	const { error, response } = await client.POST('/auth/login-magic-link', {
		body: { token },
		fetch
	});

	const parsed = parseResponseCookies(response);
	if (parsed.length > 0) {
		applyResponseCookies(cookies, parsed);
	}

	if (error) {
		console.error('Magic link login error:', response.status, response.statusText);
		return {
			errorMessage: INVALID_LINK_MESSAGE
		};
	}

	redirect(303, '/');
};
