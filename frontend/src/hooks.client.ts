import type { HandleClientError } from '@sveltejs/kit';

import {
	PUBLIC_SENTRY_DSN,
	PUBLIC_SENTRY_ENVIRONMENT,
	PUBLIC_SENTRY_TRACES_SAMPLE_RATE
} from '$env/static/public';
import { readStorage, writeStorage } from '$lib/utils/safeStorage';
import * as Sentry from '@sentry/sveltekit';

// Server errors belong to the backend, which reports them with a full stack
// trace and request context; a frontend mirror is a duplicate with none of that,
// and a transient gateway blip (502/503/504) or the 503 the `(protected)` layout
// throws when the backend is unreachable is an expected network condition, not an
// app bug. Sentry's SvelteKit load wrapper reports every HttpError with status
// >= 500, which would file each of these as a GlitchTip issue — so drop them.
// A SvelteKit HttpError is the only thing here carrying a numeric `status`; a
// genuine frontend JS bug is a real Error (no `status`) and still reports.
// See https://swiftmade.co/blog/2026-01-05-sentry-error-reporting-best-practices/
function isServerSideHttpError(exception: unknown): boolean {
	if (!exception || typeof exception !== 'object') {
		return false;
	}
	const status = (exception as { status?: unknown }).status;
	return typeof status === 'number' && status >= 500;
}

// A `fetch` that fails at the network layer — offline, connection reset, DNS, or
// a request cancelled because the user navigated away mid-load — rejects with a
// `TypeError`, and the message is the only discriminator the fetch spec offers.
// openapi-fetch only returns `{ error }` for HTTP responses (4xx/5xx); a network
// failure propagates this raw `TypeError` unchanged. Each engine words it its own
// way: Chromium "Failed to fetch", Firefox "NetworkError when attempting to fetch
// resource.", Safari "Load failed". These prefixes mirror the allowlist in the
// canonical `is-network-error` package; the Node/Deno wordings it also carries
// don't occur in a browser, so they're omitted.
//
// We match the prefix, not the whole string, because Sentry's fetch instrumentation
// appends the origin as a suffix ("NetworkError when attempting to fetch resource.
// (app.fancom.info)") — a mutation that makes `is-network-error`'s exact match miss
// this very error (getsentry/sentry-javascript#18449). `startsWith` absorbs that
// suffix while still anchoring at the start, so it can't match one of these phrases
// buried mid-message.
//
// When such an error escapes a `load` (SvelteKit's wrapper reports it unhandled) it
// is the same expected network condition as the 5xx blip above — the offline-first
// shell already falls back to cache and live reachability — not an app bug, so drop
// it. Safe here specifically: every API call is same-origin, so this is never the
// CORS misconfiguration a cross-origin "Failed to fetch" could hide, and a failed
// chunk load is recovered separately by the `vite:preloadError` handler below.
// See https://swiftmade.co/blog/2026-01-05-sentry-error-reporting-best-practices/
const NETWORK_FETCH_ERROR_PREFIXES = [
	'Failed to fetch',
	'NetworkError when attempting to fetch resource',
	'Load failed'
];

function isNetworkFetchError(exception: unknown): boolean {
	if (!(exception instanceof TypeError)) {
		return false;
	}
	return NETWORK_FETCH_ERROR_PREFIXES.some((prefix) => exception.message.startsWith(prefix));
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
			if (isServerSideHttpError(hint?.originalException)) {
				return null;
			}

			if (isNetworkFetchError(hint?.originalException)) {
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
const PRELOAD_RELOAD_MARKER = 'preload-error-reloaded-at';
const PRELOAD_RELOAD_WINDOW_MS = 30_000;

addEventListener('vite:preloadError', (event) => {
	const lastReloadAt = Number(readStorage('session', PRELOAD_RELOAD_MARKER)) || 0;
	if (Date.now() - lastReloadAt < PRELOAD_RELOAD_WINDOW_MS) return;
	// Only auto-recover when the marker can be persisted. A browser whose
	// sessionStorage is blocked (storage-partitioned in-app browsers) is exactly
	// where an unguarded reload would spin, so there we leave the error to surface.
	if (!writeStorage('session', PRELOAD_RELOAD_MARKER, String(Date.now()))) return;

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
