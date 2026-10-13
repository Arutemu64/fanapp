import { useIntervalFn } from '@vueuse/core';
import { ref } from 'vue';

// Countdown timer for "resend code" buttons: blocks repeat sends for a fixed
// number of seconds, ticking down once per second. Shared by the verify-code
// login step and the change-email modal.
const DEFAULT_COOLDOWN_SECONDS = 60;

export function useResendCooldown(seconds: number = DEFAULT_COOLDOWN_SECONDS) {
	// Seconds left before another send is allowed; 0 means ready.
	const remaining = ref(0);

	// useIntervalFn clears itself when the owning scope (component) is disposed, so a
	// countdown left running (e.g. the modal closed mid-cooldown) can't leak a timer.
	const ticker = useIntervalFn(
		() => {
			if (remaining.value > 0) {
				remaining.value -= 1;
			} else {
				ticker.pause();
			}
		},
		1000,
		{ immediate: false }
	);

	function start(): void {
		remaining.value = seconds;
		// resume() is a no-op while active, so a second start() would keep the old
		// phase; restart the timer so the first tick is a full second away.
		ticker.pause();
		ticker.resume();
	}

	// Cancel the ticking interval, leaving `remaining` as-is.
	function stop(): void {
		ticker.pause();
	}

	function reset(): void {
		ticker.pause();
		remaining.value = 0;
	}

	return { remaining, start, stop, reset };
}
