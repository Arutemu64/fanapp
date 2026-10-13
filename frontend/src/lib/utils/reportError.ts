import * as Sentry from '@sentry/vue';

import { PUBLIC_SENTRY_DSN } from '#lib/env.js';

// Server errors belong to the backend, which reports them with a full stack
// trace and request context; a frontend mirror is a duplicate with none of that,
// and a transient gateway blip (502/503/504) or the 503 the `(protected)` guard
// raises when the backend is unreachable is an expected network condition, not an
// app bug. An `HttpError` is the only thing here carrying a numeric `status`; a
// genuine frontend JS bug is a real Error (no `status`) and still reports.
// See https://swiftmade.co/blog/2026-01-05-sentry-error-reporting-best-practices/
export function isServerSideHttpError(exception: unknown): boolean {
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

export function isStaleChunkError(exception: unknown): boolean {
	if (!exception) return false;
	const message =
		typeof exception === 'string' ? exception : (exception as { message?: unknown }).message;
	return typeof message === 'string' && STALE_CHUNK_MESSAGE.test(message);
}

// A short reference the error screen shows, so a user's "код ошибки" in a
// feedback message finds the matching GlitchTip event (tagged `error_id`).
// `crypto.randomUUID` needs Safari 15.4+, so older browsers fall back to Math.random.
function createErrorId(): string {
	if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
		return crypto.randomUUID().slice(0, 8);
	}
	return Math.random().toString(16).slice(2, 10);
}

/**
 * Report an unexpected error and return the reference to show the user. The
 * reference is only returned when an event was actually sent: no DSN, or an
 * error `beforeSend` drops (a stale chunk, an error carrying a 5xx `status`),
 * would leave the user quoting an id nobody can look up.
 */
export function reportUnexpectedError(error: unknown): string | undefined {
	if (!PUBLIC_SENTRY_DSN || isStaleChunkError(error) || isServerSideHttpError(error)) {
		return undefined;
	}
	const errorId = createErrorId();
	Sentry.captureException(error, { tags: { error_id: errorId } });
	return errorId;
}
