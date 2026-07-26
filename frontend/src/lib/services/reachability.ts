import { browser } from '$app/environment';
import { PUBLIC_API_URL } from '$env/static/public';
import { timeoutSignal } from '$lib/utils/fetchTimeout';
import { createSubscriber } from 'svelte/reactivity';

/**
 * Active server-reachability tracking.
 *
 * `navigator.onLine` only knows whether a network interface exists — it reports
 * online on a connected-but-dead VPN or captive WiFi, where the backend is in
 * fact unreachable. This module instead probes a cheap, unauthenticated health
 * endpoint and treats *getting any response back* as proof we can reach the
 * server. State is module-global (not Svelte context) so universal `load`
 * functions can read it synchronously to skip a doomed network call.
 */

const HEALTH_URL = `${PUBLIC_API_URL}/debug/health`;
const PROBE_TIMEOUT_MS = 3000;

// Optimistic default so the very first paint still attempts the network; the
// first probe corrects it within PROBE_TIMEOUT_MS.
let reachable = true;
const listeners = new Set<() => void>();

/** Last known reachability. */
export function isReachable(): boolean {
	return reachable;
}

/** Update reachability from a known outcome (e.g. a load's fetch result). */
export function markReachable(value: boolean): void {
	if (reachable === value) return;
	reachable = value;
	for (const listener of listeners) listener();
}

/** Subscribe to reachability changes; returns an unsubscribe function. */
export function onReachableChange(listener: () => void): () => void {
	listeners.add(listener);
	return () => listeners.delete(listener);
}

// Bridges the listener set above into Svelte's reactivity, so a component can
// read reachability in a $derived instead of mirroring it into $state from an
// $effect. One subscription is shared however many readers there are, and it is
// torn down when the last of them goes away.
const subscribeReachable = createSubscriber((update) => onReachableChange(update));

/**
 * Reachability as a *reactive* read, for components and deriveds.
 *
 * `isReachable()` stays the plain read: `load` functions run outside any effect,
 * where subscribing would do nothing, and they only need the current value.
 */
export const reachability = {
	get current(): boolean {
		subscribeReachable();
		return reachable;
	}
};

let inflight: Promise<boolean> | null = null;

/**
 * Probe the health endpoint. A real CORS request (default mode) — not `no-cors`
 * — so the response is non-opaque and only succeeds when the *backend* answers:
 * in prod the API is same-origin; in dev the backend returns the frontend's
 * `Access-Control-Allow-Origin`. A captive portal intercepting the request
 * serves its own page *without* our CORS header, so the browser rejects it and
 * we correctly fall offline (an opaque `no-cors` probe would wrongly accept it).
 * Any HTTP status counts as reachable — even a 5xx means the server responded.
 * A network failure or timeout rejects and marks us offline. Concurrent calls
 * share one request.
 */
export function probeReachability(): Promise<boolean> {
	if (!browser) return Promise.resolve(true);
	if (inflight) return inflight;

	inflight = fetch(HEALTH_URL, {
		method: 'GET',
		cache: 'no-store',
		signal: timeoutSignal(PROBE_TIMEOUT_MS)
	})
		.then(() => {
			markReachable(true);
			return true;
		})
		.catch(() => {
			markReachable(false);
			return false;
		})
		.finally(() => {
			inflight = null;
		});

	return inflight;
}
