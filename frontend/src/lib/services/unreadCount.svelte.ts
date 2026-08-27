import { createApiClient } from '$lib/api';
import { createContext } from 'svelte';

const [getUnread, setUnread] = createContext<UnreadCountService>();

/**
 * Shared unread-notification count for the app shell. The bell renders it as a
 * badge and the notifications page clears it on open, so the two surfaces must
 * agree — a component-local count in each would let visiting the page leave a
 * stale badge on the bell. Scoped to the (app) layout via context (not a module
 * singleton), so it unmounts on logout and never leaks into the next session.
 *
 * The server's unread-count endpoint is the single source of truth: every change
 * (an SSE notification, a reconnect, a mark-read) calls refresh(), and the badge
 * converges to the server total within a round-trip. There is deliberately no
 * optimistic local delta — a delta and an authoritative total can't be ordered
 * against each other without an "as-of" token the endpoint doesn't return, so
 * mixing them leaves the badge off by one (a live increment racing a reconnect
 * refresh would either be lost or discard the reconciliation). The push toast
 * already signals a notification arrived, so the badge trailing it by a request
 * is fine.
 */
export class UnreadCountService {
	#count = $state(0);
	// True once an authoritative value (a clear, or a successful server refresh) has
	// been established. After that the provisional streamed seed must not apply — the
	// initial count is otherwise indistinguishable from an authoritative zero.
	#hasAuthoritativeValue = false;
	#inFlight = false;
	#pending = false;
	// Bumped by every authoritative local write (clear). A refresh() snapshots
	// it and drops its response if a write landed while the GET was in flight, so a
	// stale total can't overwrite the zero that "mark all read" just established.
	// Safe here precisely because the only local writes are authoritative values,
	// not deltas: a write that races a refresh is strictly newer, so discarding the
	// older in-flight response is correct (an earlier attempt guarded an optimistic
	// increment this way and wrongly discarded reconnect reconciliations — there is
	// no such delta now).
	#generation = 0;
	readonly #client = createApiClient();

	get count() {
		return this.#count;
	}

	// Provisional seed from the streamed layout load (see (app)/+layout.svelte).
	// Applies only until an authoritative value lands, so a late seed can never
	// overwrite a fresher server read — including an authoritative zero. Leaves the
	// generation untouched so a refresh already in flight still wins over the seed.
	seed(count: number) {
		if (this.#hasAuthoritativeValue) return;
		this.#count = Math.max(0, count);
	}

	// Marking every notification read zeros the server side, so reflect it at once
	// rather than waiting for the refresh round-trip.
	clear() {
		this.#hasAuthoritativeValue = true;
		this.#count = 0;
		this.#generation += 1;
	}

	// Authoritative reconcile with the server, coalesced: a call while one is in
	// flight schedules exactly one follow-up instead of a parallel request, so a
	// burst of SSE events costs at most two round-trips and the freshest response
	// is the one that sticks (requests never overlap, so none can arrive out of
	// order and regress the count).
	async refresh(): Promise<void> {
		if (this.#inFlight) {
			this.#pending = true;
			return;
		}
		this.#inFlight = true;
		const generationAtStart = this.#generation;
		try {
			const { data, error, response } = await this.#client.GET('/notifications/unread-count');
			if (!error && response.ok && data && this.#generation === generationAtStart) {
				this.#hasAuthoritativeValue = true;
				this.#count = data.count;
			}
		} catch (error) {
			console.error('Failed to load unread count', error);
		} finally {
			this.#inFlight = false;
			if (this.#pending) {
				this.#pending = false;
				void this.refresh();
			}
		}
	}
}

export function setUnreadCountService() {
	const service = new UnreadCountService();
	setUnread(service);
	return service;
}

export function getUnreadCountService() {
	return getUnread();
}
