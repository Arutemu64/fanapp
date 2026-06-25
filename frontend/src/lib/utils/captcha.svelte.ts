// Invisible-captcha gate shared by the login forms. When the user submits
// before Turnstile has produced a token, we "hold" the action and let the
// caller's $effect re-fire it once the token lands — so the user never taps
// twice. The timeout is a safety net: if the widget never resolves (network or
// script error), we stop waiting and surface a retryable error.
const DEFAULT_CAPTCHA_WAIT_TIMEOUT_MS = 10000;

export class CaptchaGate {
	// True while a submit is parked waiting for the captcha token.
	awaitingCaptcha = $state(false);

	#timer: ReturnType<typeof setTimeout> | undefined;
	#timeoutMs: number;

	constructor(timeoutMs: number = DEFAULT_CAPTCHA_WAIT_TIMEOUT_MS) {
		this.#timeoutMs = timeoutMs;
	}

	/**
	 * Park the action and arm the safety-net timeout. `onTimeout` runs only if
	 * the token never arrives in time (the gate is still waiting when it fires).
	 */
	hold(onTimeout: () => void): void {
		this.awaitingCaptcha = true;
		this.clear();
		this.#timer = setTimeout(() => {
			if (this.awaitingCaptcha) {
				this.awaitingCaptcha = false;
				onTimeout();
			}
		}, this.#timeoutMs);
	}

	// Stop waiting (token arrived, validation failed, or the form was reset).
	release(): void {
		this.awaitingCaptcha = false;
		this.clear();
	}

	// Cancel the pending timeout without touching the waiting flag. Call from
	// onMount/onDestroy cleanup to avoid a leaked timer.
	clear(): void {
		clearTimeout(this.#timer);
		this.#timer = undefined;
	}
}
