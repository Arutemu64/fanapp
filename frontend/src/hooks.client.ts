import type { HandleClientError } from '@sveltejs/kit';

import {
	PUBLIC_SENTRY_DSN,
	PUBLIC_SENTRY_ENVIRONMENT,
	PUBLIC_SENTRY_TRACES_SAMPLE_RATE
} from '$env/static/public';
import * as Sentry from '@sentry/sveltekit';

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

// Vite dispatches `vite:preloadError` when a dynamically imported chunk fails to
// load. For this app that is almost always a boot node (root layout / error page)
// dropping on a flaky mobile connection before the SW has it cached, and
// occasionally version skew after a deploy removed the old hashed chunk a still-open
// document points at. SvelteKit self-heals this during client-side navigation (it
// reloads on a detected version change), but not on the very first load — there the
// rejection instead surfaces to `handleError` below and strands the user on the error
// page. Recover the way Vite recommends: a full-page reload re-requests the shell
// (served `no-cache`, see frontend/nginx.conf) and its chunks.
// https://vite.dev/guide/build#load-error-handling
//
// The reload is guarded against looping: if the chunk is genuinely unreachable the
// reload would fail identically, so we record each attempt and skip a fresh one
// within a short window, letting a persistent failure fall through to the error page.
// We only auto-recover when the marker can be persisted — a browser whose
// sessionStorage throws (storage-partitioned in-app browsers) is exactly where an
// unguarded reload would spin, so there we leave the error to surface instead.
const PRELOAD_RELOAD_MARKER = 'preload-error-reloaded-at';
const PRELOAD_RELOAD_WINDOW_MS = 30_000;

addEventListener('vite:preloadError', (event) => {
	try {
		const lastReloadAt = Number(sessionStorage.getItem(PRELOAD_RELOAD_MARKER)) || 0;
		if (Date.now() - lastReloadAt < PRELOAD_RELOAD_WINDOW_MS) return;
		sessionStorage.setItem(PRELOAD_RELOAD_MARKER, String(Date.now()));
	} catch {
		// sessionStorage unavailable — can't guard against a loop, so don't reload.
		return;
	}

	// Stop Vite from re-throwing so this recovered failure isn't also reported to Sentry.
	event.preventDefault();
	location.reload();
});

export const handleError: HandleClientError = Sentry.handleErrorWithSentry(({ error }) => {
	const err = error as { code?: string } | undefined;
	// Localized Russian error response to fulfill the Russian Copy policy
	return {
		message: 'Произошла непредвиденная ошибка в приложении. Мы уже работаем над её устранением.',
		code: err?.code ?? 'UNKNOWN'
	};
});
