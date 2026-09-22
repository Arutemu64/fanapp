import { onlineManager } from '@tanstack/svelte-query';
import { createSubscriber } from 'svelte/reactivity';

// Bridges TanStack Query's onlineManager into Svelte's reactivity, so a component
// can read connectivity in a $derived instead of mirroring it into $state from an
// $effect. One subscription is shared however many readers there are, and it is
// torn down when the last of them goes away.
const subscribeOnline = createSubscriber((update) => onlineManager.subscribe(update));

/**
 * Connectivity as a *reactive* read, for components and deriveds.
 *
 * Reads the same signal that decides whether a query may run, so the UI can never
 * disagree with the data layer. Available without the OfflineService context,
 * which is why ErrorState (rendered outside the app shell) uses it.
 *
 * `onlineManager.isOnline()` stays the plain read for `load` functions, which run
 * outside any effect where subscribing would do nothing.
 */
export const online = {
	get current(): boolean {
		subscribeOnline();
		return onlineManager.isOnline();
	}
};
