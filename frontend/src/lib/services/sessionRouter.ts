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
		await goto(`/login?${LOGIN_NEXT_PARAM}=${encodeURIComponent(next)}`);
	}
};
