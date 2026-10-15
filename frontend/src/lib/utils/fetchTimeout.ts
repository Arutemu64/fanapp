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

/** Default budget for a first-paint API call before we fall back to cache. */
export const FIRST_PAINT_TIMEOUT_MS = 3500;

/**
 * Settle with `promise`, or reject with the TimeoutError a native timeout signal
 * would carry (`isConnectionFailure` recognises it) once `ms` have passed. The
 * work is not cancelled: it keeps running and may still land after the timeout.
 */
export function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
	let timer: ReturnType<typeof setTimeout> | undefined;
	const budget = new Promise<never>((_, reject) => {
		timer = setTimeout(() => reject(new DOMException('signal timed out', 'TimeoutError')), ms);
	});
	return Promise.race([promise, budget]).finally(() => clearTimeout(timer));
}
