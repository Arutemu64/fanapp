import { type Interval, useInterval } from '#lib/utils/useInterval.js';

const DEFAULT_COOLDOWN_SECONDS = 60;

export class ResendCooldown {
	remaining = $state(0);

	readonly #seconds: number;
	readonly #ticker: Interval;

	constructor(seconds: number = DEFAULT_COOLDOWN_SECONDS) {
		this.#seconds = seconds;
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

	stop(): void {
		this.#ticker.stop();
	}

	reset(): void {
		this.#ticker.stop();
		this.remaining = 0;
	}
}
