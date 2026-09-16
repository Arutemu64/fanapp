import { isReachable, onReachableChange } from '$lib/services/reachability';
import { onlineManager } from '@tanstack/svelte-query';

/**
 * Drive TanStack Query's online state from our backend reachability probe rather
 * than its default `navigator.onLine` listeners.
 *
 * `navigator.onLine` only says an interface exists, so on a captive portal or a
 * dead VPN it reports online and every query would fetch into a black hole
 * instead of pausing and serving its persisted copy. `reachability.ts` answers
 * the question that actually matters — did the backend respond — and is already
 * kept fresh by the offline service's probes, the `online`/`offline` events and
 * foregrounding.
 *
 * Call once from the root layout. TanStack keeps a single event listener, so the
 * returned teardown only has to undo the subscription this installed (dev HMR
 * re-creates the layout).
 */
export function bindOnlineManager(): () => void {
	let unsubscribe: (() => void) | undefined;

	onlineManager.setEventListener((setOnline) => {
		setOnline(isReachable());
		unsubscribe = onReachableChange(() => setOnline(isReachable()));
		return unsubscribe;
	});

	return () => {
		unsubscribe?.();
		unsubscribe = undefined;
	};
}
