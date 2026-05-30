import * as Sentry from '@sentry/sveltekit';

const dsn = process.env.PUBLIC_SENTRY_DSN;

if (dsn) {
	Sentry.init({
		dsn,
		environment: process.env.SENTRY_ENVIRONMENT || 'production',
		release: process.env.SENTRY_RELEASE,
		tracesSampleRate: parseFloat(process.env.SENTRY_TRACES_SAMPLE_RATE || '0.1'),
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
