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

/**
 * Statuses a reverse proxy returns when it is up but the backend behind it is
 * not: the request never reached a working app server, so it means the same
 * thing as a network failure — the backend is unreachable, not that it processed
 * the request and rejected it. Deliberately excludes a plain 500: there the
 * backend answered, so it is reachable and the app must not reframe to offline.
 */
const BACKEND_UNREACHABLE_STATUSES = new Set([502, 503, 504]);

export function isBackendUnreachableStatus(status: number): boolean {
	return BACKEND_UNREACHABLE_STATUSES.has(status);
}

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

// Epoch millis of the last API request that reached the backend. Drives the
// concurrency guard below; the health probe deliberately bypasses it.
let lastRequestReachableAt = Number.NEGATIVE_INFINITY;

/**
 * Record reachability from a *normal API request* outcome (the client
 * middleware), as opposed to the health probe which is authoritative and calls
 * {@link markReachable} directly.
 *
 * A success is authoritative — the backend answered — so it always marks us
 * reachable and remembers when. A failure is only *suggestive*: several requests
 * run concurrently per navigation (e.g. the notification preview alongside its
 * unread count), and one slow endpoint timing out after another has already
 * succeeded is not an outage. So a failure marks us unreachable only when no
 * request has succeeded within `windowMs` — long enough to span a concurrent
 * request's own timeout budget. If the backend is genuinely down every request
 * fails, no success lands, and the guard lapses; the health probe remains the
 * arbiter either way.
 */
export function reportRequestReachability(ok: boolean, windowMs: number): void {
	if (ok) {
		lastRequestReachableAt = Date.now();
		markReachable(true);
		return;
	}
	if (Date.now() - lastRequestReachableAt < windowMs) return;
	markReachable(false);
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
 * Device-level connectivity (`navigator.onLine`), as a *reactive* read.
 *
 * Unlike `reachable` (a server probe), this only says whether a network
 * interface exists — it reports online on a captive portal or dead VPN. Reading
 * it alongside `current` lets the UI tell "the device has no internet" apart
 * from "the device is online but the server can't be reached", so an outage is
 * never miscast as the user's connection dropping. A `false` here is a
 * trustworthy negative (the device really is offline); a `true` is not.
 */
function deviceOnlineNow(): boolean {
	// SSR / non-browser: assume online so the first paint still attempts the network.
	return typeof navigator === 'undefined' ? true : navigator.onLine;
}

const subscribeDeviceOnline = createSubscriber((update) => {
	window.addEventListener('online', update);
	window.addEventListener('offline', update);
	return () => {
		window.removeEventListener('online', update);
		window.removeEventListener('offline', update);
	};
});

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
	},
	get deviceOnline(): boolean {
		subscribeDeviceOnline();
		return deviceOnlineNow();
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
