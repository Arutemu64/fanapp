import type { HandleClientError } from '@sveltejs/kit';

import { PUBLIC_SENTRY_DSN } from '$env/static/public';
import * as Sentry from '@sentry/sveltekit';

if (PUBLIC_SENTRY_DSN) {
	// These build-time Sentry vars aren't in Vite's typed env, so they come
	// through as `any`; read them through a narrowed view to keep types safe.
	const buildEnv = import.meta.env as Record<string, string | undefined>;
	Sentry.init({
		dsn: PUBLIC_SENTRY_DSN,
		environment: buildEnv.SENTRY_ENVIRONMENT || 'production',
		release: buildEnv.SENTRY_RELEASE,
		tracesSampleRate: parseFloat(buildEnv.SENTRY_TRACES_SAMPLE_RATE || '0.1'),
		beforeSend(event) {
			// Scrub potential PII from request headers and cookies
			if (event.request) {
				delete event.request.cookies;
				if (event.request.headers) {
					const scrubbedHeaders = { ...event.request.headers };
					const sensitive = ['cookie', 'authorization', 'x-api-key', 'x-auth-token'];
					for (const key of Object.keys(scrubbedHeaders)) {
						if (sensitive.includes(key.toLowerCase())) {
							scrubbedHeaders[key] = '[Filtered]';
						}
					}
					event.request.headers = scrubbedHeaders;
				}
			}
			return event;
		}
	});
}

export const handleError: HandleClientError = Sentry.handleErrorWithSentry(({ error }) => {
	const err = error as { code?: string } | undefined;
	// Localized Russian error response to fulfill the Russian Copy policy
	return {
		message: 'Произошла непредвиденная ошибка в приложении. Мы уже работаем над её устранением.',
		code: err?.code ?? 'UNKNOWN'
	};
});
