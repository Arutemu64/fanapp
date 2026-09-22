import type { QueryClient } from '@tanstack/svelte-query';

import { flushPendingLogout } from '$lib/utils/pendingLogout';
import { requestReconnectRefresh } from '$lib/utils/reconnectRefresh';
import { onlineManager } from '@tanstack/svelte-query';
import { createContext } from 'svelte';

/**
 * Reactive view over connectivity, driving the offline banner and the write
 * gates, plus the side effects a recovery owes: flushing a logout queued while
 * offline and catching up on data that changed while we were away.
 *
 * Connectivity itself is TanStack Query's `onlineManager`, the same signal that
 * decides whether a query may run — so the banner can never disagree with what
 * the data layer is doing. Note it is `navigator.onLine`-based, which reports
 * online on a captive portal or a connected-but-dead VPN.
 */
class OfflineService {
	#online = $state(onlineManager.isOnline());
	#unsubscribe: (() => void) | null = null;
	readonly #queryClient: QueryClient;

	constructor(queryClient: QueryClient) {
		this.#queryClient = queryClient;

		this.#unsubscribe = onlineManager.subscribe((online) => {
			const wasOnline = this.#online;
			this.#online = online;
			if (!wasOnline && online) this.#handleRecovery();
		});

		// Fire any logout queued while offline. A boot that is already online never
		// crosses the offline→online edge above, so flush here too; when offline this
		// is a no-op and the edge handler picks it up on reconnect.
		void flushPendingLogout();
	}

	/** True when the device reports a network connection. */
	get isOnline(): boolean {
		return this.#online;
	}

	/**
	 * Drop the subscription. The root layout lives for the app's lifetime in
	 * production, but dev HMR re-creates it — without this each cycle would stack
	 * another subscriber (same reason EventsClient has destroy()).
	 */
	destroy() {
		this.#unsubscribe?.();
		this.#unsubscribe = null;
	}

	#handleRecovery() {
		// Revoke a session the user logged out of while offline, before the refetch
		// below re-runs /me — the pending flag keeps identity logged-out until this
		// clears, so there's no "logged back in" flicker in between.
		void flushPendingLogout();

		// Live SSE events only cover data that *changed* server-side; this catches
		// the rest. Debounced and shared with the SSE reconnect path so a flapping
		// connection can't trigger refetch storms.
		requestReconnectRefresh(this.#queryClient);
	}
}

const [getOffline, setOffline] = createContext<OfflineService>();

/** Create and set the OfflineService in context (call in the root layout). */
export function setOfflineService(queryClient: QueryClient) {
	const service = new OfflineService(queryClient);
	setOffline(service);
	return service;
}

export function getOfflineService() {
	return getOffline();
}
