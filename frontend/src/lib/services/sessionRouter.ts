import { goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { page } from '$app/state';

import { LOGIN_NEXT_PARAM, sanitizeNextPath } from '#lib/utils/auth.js';

import type { SessionRouter } from './session.js';

export const browserSessionRouter: SessionRouter = {
	async goToLoginTarget() {
		const next = sanitizeNextPath(new URL(window.location.href).searchParams.get(LOGIN_NEXT_PARAM));
		// `next` was captured by the (protected) guard from `url.pathname`, which is
		// already base-qualified — wrapping it in resolve() would prepend the base
		// path a second time. It is sanitized to an in-app path above.
		const home = resolve('');
		// goto rejects a path that matches no route, and `next` comes from the URL, so
		// a hand-edited one can name anything: land on home rather than strand the
		// now-signed-in user on the login form.
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
