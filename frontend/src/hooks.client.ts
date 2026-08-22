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

// A dynamically imported chunk that fails to load. Each browser words it
// differently, so we match on the parts that are stable across engines:
// Chrome/Edge "Failed to fetch dynamically imported module", Firefox "error
// loading dynamically imported module", Safari "Importing a module script failed".
// https://bugzilla.mozilla.org/show_bug.cgi?id=1826110 (Firefox wording)
// https://github.com/sveltejs/kit/issues/5208 (Safari wording)
const STALE_CHUNK_MESSAGE = /dynamically imported module|Importing a module script failed/i;

function isStaleChunkError(exception: unknown): boolean {
	if (!exception) return false;
	const message =
		typeof exception === 'string' ? exception : (exception as { message?: unknown }).message;
	return typeof message === 'string' && STALE_CHUNK_MESSAGE.test(message);
}

// `navigator.onLine === false` is a trustworthy negative — the device really has
// no connection (a `true` can still lie behind a captive portal, so we never infer
// "online" from it, only "offline" from `false`). `navigator` is always present in
// the client hooks, but the guard keeps this safe if it is ever called elsewhere.
function isDeviceOffline(): boolean {
	return typeof navigator !== 'undefined' && navigator.onLine === false;
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

			// A stale-chunk load failure is version skew after a deploy, not an app
			// bug: the recovery below reloads the user onto the fresh build, and a
			// chunk that stays unreachable is re-filed once as a distinct message.
			// Drop the raw TypeError here so it never files as a JS error — the
			// SvelteKit load wrapper, the browser's unhandledrejection handler and
			// Vite's re-thrown preload error all funnel through here.
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

// A dynamically imported chunk can fail to load two ways: a boot node (root
// layout / error page) dropping on a flaky mobile connection before the SW has it
// cached, or version skew after a deploy removed the old hashed chunk a still-open
// document points at. Recover the way Vite recommends — a full-page reload
// re-requests the shell (served `no-cache`, see frontend/nginx.conf) and its
// fresh chunks. https://vite.dev/guide/build#load-error-handling
//
// The reload is guarded against looping: if the chunk is genuinely unreachable the
// reload would fail identically, so we record each attempt and skip a fresh one
// within a short window.
const PRELOAD_RELOAD_MARKER = 'preload-error-reloaded-at';
const PRELOAD_RELOAD_WINDOW_MS = 30_000;

type StaleChunkRecovery = 'reload' | 'persistent' | 'blocked';

function planStaleChunkRecovery(): StaleChunkRecovery {
	const lastReloadAt = Number(readStorage('session', PRELOAD_RELOAD_MARKER)) || 0;
	// Already reloaded once within the window and the chunk is still failing — a
	// second reload can't help, so this is a deploy that left a chunk unreachable.
	if (Date.now() - lastReloadAt < PRELOAD_RELOAD_WINDOW_MS) return 'persistent';
	// Only auto-recover when the marker can be persisted. A browser whose
	// sessionStorage is blocked (storage-partitioned in-app browsers) is exactly
	// where an unguarded reload would spin, so there we leave the error to surface.
	if (!writeStorage('session', PRELOAD_RELOAD_MARKER, String(Date.now()))) return 'blocked';
	return 'reload';
}

// Shared recovery for a stale-chunk failure, whichever event surfaced it.
// `preventDefault` is called only when we reload: for `vite:preloadError` it also
// resolves the import to `undefined`, so on the non-reload paths we must let the
// event run its course (Vite re-throws → SvelteKit renders the error page).
function recoverFromStaleChunk(preventDefault: () => void): void {
	const plan = planStaleChunkRecovery();
	if (plan === 'reload') {
		preventDefault();
		location.reload();
		return;
	}
	if (plan === 'persistent' && !isDeviceOffline()) {
		// Re-file the guarded-out failure as a distinct, deduped signal that a deploy
		// left a chunk unreachable — the raw TypeError is dropped in `beforeSend`.
		// Skip it when the device is offline: there the reload simply couldn't reach
		// the network again, an expected offline blip (the error page renders "Нет
		// интернета") rather than a chunk a deploy actually removed. Same stance as
		// the 5xx/offline drops above — `navigator.onLine === false` is a trustworthy
		// negative, so we only report when the device is genuinely online.
		Sentry.captureMessage('Stale chunk unreachable after recovery reload', 'warning');
	}
	// 'persistent' / 'blocked': let the failure fall through to the error page.
}

// Vite dispatches `vite:preloadError` when a chunk it preloads fails. SvelteKit
// also self-heals this during client-side navigation (it reloads on a detected
// version change), so this mainly catches the flaky-connection case.
addEventListener('vite:preloadError', (event) => {
	recoverFromStaleChunk(() => event.preventDefault());
});

// The same failure can instead surface as a bare unhandled rejection that never
// reaches `vite:preloadError` — e.g. the error-page node failing to import during
// initial hydration, or a speculative link preload not wrapped by Vite's preload
// helper. Without this the user is stranded on the error page and the TypeError is
// filed as an app bug (GlitchTip #19, /voting/art after a deploy).
addEventListener('unhandledrejection', (event) => {
	if (!isStaleChunkError(event.reason)) return;
	recoverFromStaleChunk(() => event.preventDefault());
});

export const handleError: HandleClientError = Sentry.handleErrorWithSentry(({ error }) => {
	const err = error as { code?: string } | undefined;
	// Localized Russian error response to fulfill the Russian Copy policy
	return {
		message: 'Произошла непредвиденная ошибка в приложении. Мы уже работаем над её устранением.',
		code: err?.code ?? 'UNKNOWN'
	};
});
