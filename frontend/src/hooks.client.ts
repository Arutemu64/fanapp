import type { HandleClientError } from '@sveltejs/kit';

import {
	PUBLIC_SENTRY_DSN,
	PUBLIC_SENTRY_ENVIRONMENT,
	PUBLIC_SENTRY_TRACES_SAMPLE_RATE
} from '$env/static/public';
import { SERVER_UNREACHABLE_CODE } from '$lib/services/reachability';
import * as Sentry from '@sentry/sveltekit';

// The `(protected)` layout throws a 503 HttpError when the backend is
// unreachable, so the offline ErrorState renders instead of bouncing a
// possibly-authenticated user to a login page that can't work offline. Sentry's
// SvelteKit load wrapper reports HttpErrors with status >= 500, which would turn
// every mobile connectivity blip into a GlitchTip issue. This is an expected
// network condition, not an application bug — recognise it by the code the
// layout attaches and drop it. A genuine backend 503 (a real HTTP_ERROR without
// this code) still reports.
function isServerUnreachableError(exception: unknown): boolean {
	if (!exception || typeof exception !== 'object') {
		return false;
	}
	const body = (exception as { body?: unknown }).body;
	if (!body || typeof body !== 'object') {
		return false;
	}
	return (body as { code?: unknown }).code === SERVER_UNREACHABLE_CODE;
}

// `Number('')` is 0 and `Number('half')` is NaN — neither is a sane sample rate
// to infer from a missing or fat-fingered value, so both fall back to the
// documented default. An explicit `0` (sampling off) is honoured.
const DEFAULT_TRACES_SAMPLE_RATE = 0.1;
const configuredTracesSampleRate = Number(PUBLIC_SENTRY_TRACES_SAMPLE_RATE);
const tracesSampleRate =
	PUBLIC_SENTRY_TRACES_SAMPLE_RATE && Number.isFinite(configuredTracesSampleRate)
		? configuredTracesSampleRate
		: DEFAULT_TRACES_SAMPLE_RATE;

if (PUBLIC_SENTRY_DSN) {
	Sentry.init({
		dsn: PUBLIC_SENTRY_DSN,
		environment: PUBLIC_SENTRY_ENVIRONMENT || 'production',
		// `release` is deliberately absent. The Sentry build plugin injects the
		// release name it uploaded the source maps under, and the SDK falls back to
		// that automatically — which is the only value guaranteed to match the maps.
		// Passing the key at all would break this: init spreads the caller's options
		// over its defaults, so even `release: undefined` overwrites the injected
		// value (see applyDefaultOptions in @sentry/browser).
		tracesSampleRate,
		beforeSend(event, hint) {
			if (isServerUnreachableError(hint?.originalException)) {
				return null;
			}

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
