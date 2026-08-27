import { type Interval, useInterval } from '$lib/utils/useInterval';

// Countdown timer for "resend code" buttons: blocks repeat sends for a fixed
// number of seconds, ticking down once per second. Shared by the verify-code
// login step and the change-email modal.
const DEFAULT_COOLDOWN_SECONDS = 60;

export class ResendCooldown {
	// Seconds left before another send is allowed; 0 means ready.
	remaining = $state(0);

	#seconds: number;
	#ticker: Interval;

	constructor(seconds: number = DEFAULT_COOLDOWN_SECONDS) {
		this.#seconds = seconds;
		// useInterval clears itself on component destroy, so a countdown left
		// running (e.g. the modal closed mid-cooldown) can't leak a ticking timer.
		this.#ticker = useInterval(() => {
			if (this.remaining > 0) {
				this.remaining -= 1;
			} else {
				this.#ticker.stop();
			}
		}, 1000);
	}

	start(): void {
		this.remaining = this.#seconds;
		this.#ticker.start();
	}

	// Cancel the ticking interval, leaving `remaining` as-is.
	stop(): void {
		this.#ticker.stop();
	}

	reset(): void {
		this.#ticker.stop();
		this.remaining = 0;
	}
}
