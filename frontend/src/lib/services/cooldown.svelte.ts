// Countdown timer for "resend code" buttons: blocks repeat sends for a fixed
// number of seconds, ticking down once per second. Shared by the verify-code
// login step and the change-email modal.
const DEFAULT_COOLDOWN_SECONDS = 60;

export class ResendCooldown {
	// Seconds left before another send is allowed; 0 means ready.
	remaining = $state(0);

	#interval: ReturnType<typeof setInterval> | undefined;
	#seconds: number;

	constructor(seconds: number = DEFAULT_COOLDOWN_SECONDS) {
		this.#seconds = seconds;
	}

	start(): void {
		this.remaining = this.#seconds;
		this.stop();
		this.#interval = setInterval(() => {
			if (this.remaining > 0) {
				this.remaining -= 1;
			} else {
				this.stop();
			}
		}, 1000);
	}

	// Cancel the ticking interval, leaving `remaining` as-is.
	stop(): void {
		clearInterval(this.#interval);
		this.#interval = undefined;
	}

	reset(): void {
		this.stop();
		this.remaining = 0;
	}
}
