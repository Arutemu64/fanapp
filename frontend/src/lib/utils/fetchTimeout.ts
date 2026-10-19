/**
 * An AbortSignal that fires after `ms`, used to bound API calls that have an
 * offline fallback. Without it, a request on a flaky/captive network (or an
 * installed PWA whose `navigator.onLine` wrongly reports online) can hang on
 * the TCP timeout for ~a minute before rejecting — blocking first paint.
 *
 * Prefers the native `AbortSignal.timeout`, with a manual fallback for older
 * mobile browsers that lack it.
 */
export function timeoutSignal(ms: number): AbortSignal {
	if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
		return AbortSignal.timeout(ms);
	}

	// Abort with the same TimeoutError the native signal uses, so callers (and
	// getApiErrorDetail) can tell a timeout from a deliberate abort.
	const controller = new AbortController();
	setTimeout(() => controller.abort(new DOMException('signal timed out', 'TimeoutError')), ms);
	return controller.signal;
}

/**
 * An AbortSignal that fires when any of `signals` does, with that signal's
 * reason. Prefers the native `AbortSignal.any`, with a manual fallback for the
 * older mobile browsers that lack it (Safari before 17.4).
 */
export function anySignal(signals: AbortSignal[]): AbortSignal {
	if (typeof AbortSignal.any === 'function') {
		return AbortSignal.any(signals);
	}

	const controller = new AbortController();
	for (const signal of signals) {
		if (signal.aborted) {
			controller.abort(signal.reason);
			break;
		}
		signal.addEventListener('abort', () => controller.abort(signal.reason), { once: true });
	}
	return controller.signal;
}

/** Default budget for a first-paint API call before we fall back to cache. */
export const FIRST_PAINT_TIMEOUT_MS = 3500;
