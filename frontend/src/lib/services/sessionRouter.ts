import { goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { page } from '$app/state';

import { LOGIN_NEXT_PARAM, sanitizeNextPath } from '#lib/utils/auth.js';

import type { SessionRouter } from './session.js';

export const browserSessionRouter: SessionRouter = {
	async goToLoginTarget() {
		const next = sanitizeNextPath(new URL(window.location.href).searchParams.get(LOGIN_NEXT_PARAM));
		const home = resolve('');
		try {
			// eslint-disable-next-line svelte/no-navigation-without-resolve -- next is a validated app URL with its base path and query intact.
			await goto(next ?? home);
		} catch {
			await goto(home);
		}
	},

	goHome() {
		return goto(resolve(''));
	},

	async redirectToLogin() {
		if (!page.route.id?.startsWith('/(app)/(protected)/')) return;
		const next = page.url.pathname + page.url.search;
		await goto(resolve(`login?${LOGIN_NEXT_PARAM}=${encodeURIComponent(next)}`));
	}
};
