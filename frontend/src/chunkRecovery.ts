import * as Sentry from '@sentry/vue';
import { type Router } from 'vue-router';

import { isStaleChunkError } from '#lib/utils/reportError.js';
import { readStorage, writeStorage } from '#lib/utils/safeStorage.js';

// `navigator.onLine === false` is a trustworthy negative — the device really has
// no connection (a `true` can still lie behind a captive portal, so we never infer
// "online" from it, only "offline" from `false`).
function isDeviceOffline(): boolean {
	return navigator.onLine === false;
}

// A dynamically imported chunk can fail to load two ways: a route chunk dropping
// on a flaky mobile connection before the SW has it cached, or version skew after
// a deploy removed the old hashed chunk a still-open document points at. Recover
// the way Vite recommends — a full-page reload re-requests the shell (served
// `no-cache`, see frontend/nginx.conf) and its fresh chunks.
// https://vite.dev/guide/build#load-error-handling
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
// event run its course (Vite re-throws → the error screen renders).
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
		// the network again, an expected offline blip (the error screen renders "Нет
		// интернета") rather than a chunk a deploy actually removed. Same stance as
		// the 5xx/offline drops in sentry.ts — `navigator.onLine === false` is a
		// trustworthy negative, so we only report when the device is genuinely online.
		Sentry.captureMessage('Stale chunk unreachable after recovery reload', 'warning');
	}
	// 'persistent' / 'blocked': let the failure fall through to the error screen.
}

export function installChunkRecovery(router: Router): void {
	// Vite dispatches `vite:preloadError` when a chunk it preloads fails.
	addEventListener('vite:preloadError', (event) => {
		recoverFromStaleChunk(() => event.preventDefault());
	});

	// The same failure can instead surface as a bare unhandled rejection that never
	// reaches `vite:preloadError` — e.g. a speculative import not wrapped by Vite's
	// preload helper.
	addEventListener('unhandledrejection', (event) => {
		if (!isStaleChunkError(event.reason)) return;
		recoverFromStaleChunk(() => event.preventDefault());
	});

	// A route component whose chunk fails to import rejects the navigation; the
	// router reports it here instead of as an unhandled rejection.
	router.onError((error) => {
		if (!isStaleChunkError(error)) return;
		recoverFromStaleChunk(() => {});
	});
}
