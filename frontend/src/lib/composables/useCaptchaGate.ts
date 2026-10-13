import { getCurrentScope, onScopeDispose, ref } from 'vue';

// Invisible-captcha gate shared by the login forms. When the user submits
// before the captcha has produced a token, we "hold" the action and let the
// widget's onSolve callback re-fire it once the token lands — so the user never
// taps twice. The timeout is a safety net: if the widget never resolves (network
// or script error), we stop waiting and surface a retryable error.
const DEFAULT_CAPTCHA_WAIT_TIMEOUT_MS = 10000;

export function useCaptchaGate(timeoutMs: number = DEFAULT_CAPTCHA_WAIT_TIMEOUT_MS) {
	// True while a submit is parked waiting for the captcha token.
	const awaitingCaptcha = ref(false);

	let timer: ReturnType<typeof setTimeout> | undefined;

	// Cancel the pending timeout without touching the waiting flag.
	function clear(): void {
		clearTimeout(timer);
		timer = undefined;
	}

	/**
	 * Park the action and arm the safety-net timeout. `onTimeout` runs only if
	 * the token never arrives in time (the gate is still waiting when it fires).
	 */
	function hold(onTimeout: () => void): void {
		awaitingCaptcha.value = true;
		clear();
		timer = setTimeout(() => {
			if (awaitingCaptcha.value) {
				awaitingCaptcha.value = false;
				onTimeout();
			}
		}, timeoutMs);
	}

	// Stop waiting (token arrived, validation failed, or the form was reset).
	function release(): void {
		awaitingCaptcha.value = false;
		clear();
	}

	// A timer left armed when the owning component unmounts must not fire into it.
	if (getCurrentScope()) onScopeDispose(clear);

	return { awaitingCaptcha, hold, release, clear };
}
