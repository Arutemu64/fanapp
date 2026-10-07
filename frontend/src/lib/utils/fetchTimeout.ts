/**
 * An AbortSignal that fires after `ms`, used to bound API calls a page can do
 * without (or must not wait a minute for). Without it, a request on a
 * flaky/captive network can hang on the TCP timeout for ~a minute before
 * rejecting — blocking first paint.
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

/** Budget for an optional first-paint API call the page falls back from. */
export const FIRST_PAINT_TIMEOUT_MS = 3500;

/**
 * Budget for a read the page cannot render without. Generous, so a slow venue
 * network still gets through; bounded, so a stalled one reaches the error page's
 * retry instead of an endless spinner. Past ~10 s users stop waiting anyway
 * (https://www.nngroup.com/articles/response-times-3-important-limits/).
 */
export const REQUIRED_READ_TIMEOUT_MS = 15000;
