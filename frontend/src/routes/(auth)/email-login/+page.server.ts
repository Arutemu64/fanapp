import { createApiClient } from '$lib/api';
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const INVALID_LINK_MESSAGE = 'Ссылка для входа недействительна или уже устарела.';

export const load: PageServerLoad = async ({ fetch, url }) => {
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

	if (error) {
		console.error('Magic link login error:', response.status, response.statusText);
		return {
			errorMessage: INVALID_LINK_MESSAGE
		};
	}

	redirect(303, '/');
};
