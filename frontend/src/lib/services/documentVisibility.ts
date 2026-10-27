import { createSubscriber } from 'svelte/reactivity';

const subscribeVisible = createSubscriber((update) => {
	document.addEventListener('visibilitychange', update);
	return () => document.removeEventListener('visibilitychange', update);
});

export const documentVisibility = {
	get current(): boolean {
		subscribeVisible();
		return document.visibilityState === 'visible';
	}
};
