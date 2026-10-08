import { createSubscriber } from 'svelte/reactivity';

/**
 * Wall-clock time as a *reactive* read that ticks once a minute, for relative
 * labels ("5 минут назад") that would otherwise freeze at first render while an
 * installed app stays open for hours.
 *
 * Module-global like `documentVisibility`: the time is a device fact, not user-
 * or session-scoped state. One interval is shared by every reader and cleared
 * when the last of them unmounts.
 */
const subscribeMinute = createSubscriber((update) => {
	const id = setInterval(update, 60_000);
	return () => clearInterval(id);
});

export const minuteClock = {
	get now(): number {
		subscribeMinute();
		return Date.now();
	}
};
