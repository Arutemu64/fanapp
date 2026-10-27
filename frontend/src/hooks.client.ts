import type { HandleClientError } from '@sveltejs/kit/hooks';

import {
	PUBLIC_SENTRY_DSN,
	PUBLIC_SENTRY_ENVIRONMENT,
	PUBLIC_SENTRY_TRACES_SAMPLE_RATE
} from '$app/env/public';
import * as Sentry from '@sentry/sveltekit';

import { m } from '#lib/paraglide/messages.js';
import { readStorage, writeStorage } from '#lib/utils/safeStorage.js';

function isServerSideHttpError(exception: unknown): boolean {
	if (typeof exception !== 'object' || exception === null) {
		return false;
	}
	const status = (exception as { status?: unknown }).status;
	return typeof status === 'number' && status >= 500;
}

const STALE_CHUNK_MESSAGE = /dynamically imported module|Importing a module script failed/i;

function isStaleChunkError(exception: unknown): boolean {
	let message: unknown = exception;
	if (typeof exception === 'object' && exception !== null) {
		message = (exception as { message?: unknown }).message;
	}
	return typeof message === 'string' && STALE_CHUNK_MESSAGE.test(message);
}

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
		tracesSampleRate,
		beforeSend(event, hint) {
			if (isServerSideHttpError(hint.originalException)) {
				return null;
			}

			if (isStaleChunkError(hint.originalException)) {
				return null;
			}

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

const PRELOAD_RELOAD_MARKER = 'preload-error-reloaded-at';
const PRELOAD_RELOAD_WINDOW_MS = 30_000;

type StaleChunkRecovery = 'reload' | 'persistent' | 'blocked';

function planStaleChunkRecovery(): StaleChunkRecovery {
	const lastReloadAt = Number(readStorage('session', PRELOAD_RELOAD_MARKER)) || 0;
	if (Date.now() - lastReloadAt < PRELOAD_RELOAD_WINDOW_MS) return 'persistent';
	if (!writeStorage('session', PRELOAD_RELOAD_MARKER, String(Date.now()))) return 'blocked';
	return 'reload';
}

function recoverFromStaleChunk(preventDefault: () => void): void {
	const plan = planStaleChunkRecovery();
	if (plan === 'reload') {
		preventDefault();
		location.reload();
		return;
	}
	if (plan === 'persistent' && navigator.onLine) {
		Sentry.captureMessage('Stale chunk unreachable after recovery reload', 'warning');
	}
}

addEventListener('vite:preloadError', (event) => {
	recoverFromStaleChunk(() => event.preventDefault());
});

addEventListener('unhandledrejection', (event) => {
	if (!isStaleChunkError(event.reason)) return;
	recoverFromStaleChunk(() => event.preventDefault());
});

function createErrorId(): string {
	if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
		return crypto.randomUUID().slice(0, 8);
	}
	return Math.random().toString(16).slice(2, 10);
}

export const handleError: HandleClientError = ({ kind, error }) => {
	if (kind === 'app') return;

	const err = error as { code?: string } | undefined;
	const code = err?.code ?? 'UNKNOWN';
	const message = m.app_error_fallback();

	if (
		kind === 'framework' ||
		!PUBLIC_SENTRY_DSN ||
		isStaleChunkError(error) ||
		isServerSideHttpError(error)
	) {
		return { message, code };
	}

	const errorId = createErrorId();
	Sentry.captureException(error, {
		mechanism: { type: 'auto.function.sveltekit.handle_error', handled: true },
		captureContext: { tags: { error_id: errorId } }
	});
	return { message, code, errorId };
};
