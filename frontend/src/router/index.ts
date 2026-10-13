import type { QueryClient } from '@tanstack/vue-query';

import { createRouter, createWebHistory, type RouteLocationNormalized } from 'vue-router';

import type { PageData } from '#lib/router/load.js';

import { HttpError, Redirect } from '#lib/router/load.js';
import { statusTitle } from '#lib/utils/errorTitle.js';
import { reportUnexpectedError } from '#lib/utils/reportError.js';

import { routes } from './routes/index.js';

const SITE_NAME = 'ФАН ФАН';

// The router's counterpart of SvelteKit's `load` pipeline. Each matched record
// may carry `meta.load`; they run parent → child before the navigation commits,
// each seeing what its parents returned. A loader guards (throws `redirect` /
// `error`), prefetches, and returns the page's data, which lands on the route
// location (`meta.pageData`) so it flips together with the route.
async function runLoaders(to: RouteLocationNormalized, queryClient: QueryClient): Promise<PageData> {
	let pageData: PageData = {};
	for (const record of to.matched) {
		const load = record.meta.load;
		if (!load) continue;
		const returned = await load({ to, queryClient, parent: pageData });
		if (returned) pageData = { ...pageData, ...returned };
	}
	return pageData;
}

function documentTitle(to: RouteLocationNormalized): string {
	const error = to.meta.error;
	if (error) return `${statusTitle(error.status)} (${error.status}) · ${SITE_NAME}`;
	const data = to.meta.pageData;
	if (data?.documentTitle) return data.documentTitle;
	return data?.title ? `${data.title} · ${SITE_NAME}` : SITE_NAME;
}

export function createAppRouter(queryClient: QueryClient) {
	const router = createRouter({
		history: createWebHistory(),
		routes,
		// The scroll region is <main> inside the app shell, not the window, so the
		// shell restores scroll itself (AppLayout).
		scrollBehavior: () => false
	});

	router.beforeResolve(async (to) => {
		try {
			to.meta.pageData = await runLoaders(to, queryClient);
		} catch (thrown) {
			if (thrown instanceof Redirect) return thrown.location;
			if (thrown instanceof HttpError) {
				// Expected outcomes (a 403, the offline 503) render in the shell. Server
				// errors belong to the backend, which reports them with a stack trace and
				// request context, so none of them is mirrored to Sentry here.
				to.meta.pageData = {};
				to.meta.error = { status: thrown.status, message: thrown.message, code: thrown.code };
				return;
			}
			const errorId = reportUnexpectedError(thrown);
			to.meta.pageData = {};
			to.meta.error = {
				status: 500,
				message: 'В приложении что-то сломалось. Попробуй обновить страницу.',
				code: 'UNKNOWN',
				errorId
			};
		}
	});

	router.afterEach((to) => {
		document.title = documentTitle(to);
	});

	return router;
}
