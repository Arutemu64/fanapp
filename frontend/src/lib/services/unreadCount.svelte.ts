import { createApiClient } from '$lib/api';
import { createContext } from 'svelte';

const [getUnread, setUnread] = createContext<UnreadCountService>();

/**
 * Shared unread-notification count for the app shell. The bell renders it as a
 * badge and the notifications page clears it on open, so the two surfaces must
 * agree — a component-local count in each would let visiting the page leave a
 * stale badge on the bell. Scoped to the (app) layout via context (not a module
 * singleton), so it unmounts on logout and never leaks into the next session.
 */
export class UnreadCountService {
	#count = $state(0);
	// Bumped on every local mutation (increment/clear/set). A refresh() snapshots
	// it before its request and discards the response if anything changed meanwhile,
	// so a slow count fetch can't clobber a live SSE increment that raced it — the
	// local mutation wins and the next refresh reconciles.
	#mutation = 0;
	readonly #client = createApiClient();

	get count() {
		return this.#count;
	}

	set(count: number) {
		this.#count = Math.max(0, count);
		this.#mutation += 1;
	}

	increment() {
		this.#count += 1;
		this.#mutation += 1;
	}

	clear() {
		this.#count = 0;
		this.#mutation += 1;
	}

	async refresh() {
		const mutationAtStart = this.#mutation;
		try {
			const { data, error, response } = await this.#client.GET('/notifications/unread-count');
			if (!error && response.ok && data && this.#mutation === mutationAtStart) {
				this.#count = data.count;
			}
		} catch (error) {
			console.error('Failed to load unread count', error);
		}
	}
}

export function setUnreadCountService(initialCount = 0) {
	const service = new UnreadCountService();
	service.set(initialCount);
	setUnread(service);
	return service;
}

export function getUnreadCountService() {
	return getUnread();
}
