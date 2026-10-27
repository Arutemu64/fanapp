import { createSubscriber } from 'svelte/reactivity';

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
