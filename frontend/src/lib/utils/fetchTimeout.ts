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

	const controller = new AbortController();
	setTimeout(() => controller.abort(), ms);
	return controller.signal;
}

/** Default budget for a first-paint API call before we fall back to cache. */
export const FIRST_PAINT_TIMEOUT_MS = 3500;
