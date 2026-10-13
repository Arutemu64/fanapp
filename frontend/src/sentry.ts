import * as Sentry from '@sentry/vue';
import { type App } from 'vue';
import { type Router } from 'vue-router';

import {
	PUBLIC_SENTRY_DSN,
	PUBLIC_SENTRY_ENVIRONMENT,
	PUBLIC_SENTRY_TRACES_SAMPLE_RATE
} from '#lib/env.js';
import { isServerSideHttpError, isStaleChunkError } from '#lib/utils/reportError.js';

// `Number('')` is 0 and `Number('half')` is NaN — neither is a sane sample rate
// to infer from a missing or fat-fingered value, so both fall back to the
// documented default. An explicit `0` (sampling off) is honoured.
const DEFAULT_TRACES_SAMPLE_RATE = 0.1;
const configuredTracesSampleRate = Number(PUBLIC_SENTRY_TRACES_SAMPLE_RATE);
const tracesSampleRate =
	PUBLIC_SENTRY_TRACES_SAMPLE_RATE && Number.isFinite(configuredTracesSampleRate)
		? configuredTracesSampleRate
		: DEFAULT_TRACES_SAMPLE_RATE;

export function initSentry(app: App, router: Router): void {
	if (!PUBLIC_SENTRY_DSN) return;

	Sentry.init({
		app,
		dsn: PUBLIC_SENTRY_DSN,
		environment: PUBLIC_SENTRY_ENVIRONMENT || 'production',
		integrations: [Sentry.browserTracingIntegration({ router })],
		// `release` is deliberately absent. The Sentry build plugin injects the
		// release name it uploaded the source maps under, and the SDK falls back to
		// that automatically — which is the only value guaranteed to match the maps.
		// Passing the key at all would break this: init spreads the caller's options
		// over its defaults, so even `release: undefined` overwrites the injected
		// value (see applyDefaultOptions in @sentry/browser).
		tracesSampleRate,
		beforeSend(event, hint) {
			if (isServerSideHttpError(hint?.originalException)) {
				return null;
			}

			// A stale-chunk load failure is version skew after a deploy, not an app
			// bug: the recovery in chunkRecovery.ts reloads the user onto the fresh
			// build, and a chunk that stays unreachable is re-filed once as a distinct
			// message. Drop the raw TypeError here so it never files as a JS error —
			// the router's navigation error, the browser's unhandledrejection handler
			// and Vite's re-thrown preload error all funnel through here.
			if (isStaleChunkError(hint?.originalException)) {
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
