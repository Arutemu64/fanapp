import * as Sentry from '@sentry/sveltekit';
import { env } from '$env/dynamic/public';
import type { HandleClientError } from '@sveltejs/kit';

const { PUBLIC_SENTRY_DSN } = env;

if (PUBLIC_SENTRY_DSN) {
	Sentry.init({
		dsn: PUBLIC_SENTRY_DSN,
		environment: import.meta.env.SENTRY_ENVIRONMENT || 'production',
		release: import.meta.env.SENTRY_RELEASE,
		tracesSampleRate: parseFloat(import.meta.env.SENTRY_TRACES_SAMPLE_RATE || '0.1'),
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
