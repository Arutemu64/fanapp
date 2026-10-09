import { PUBLIC_API_URL } from '$app/env/public';
import { createSubscriber } from 'svelte/reactivity';

import { timeoutSignal } from '#lib/utils/fetchTimeout.js';

/**
 * Active server-reachability tracking — the app's single answer to "are we online?".
 *
 * `navigator.onLine` only knows whether a network interface exists — it reports
 * online on a connected-but-dead VPN or captive WiFi, where the backend is in
 * fact unreachable. This module instead probes a cheap, unauthenticated health
 * endpoint and treats *getting any response back* as proof we can reach the
 * server. State is module-global (not Svelte context) so universal `load`
 * functions can read it synchronously to skip a doomed network call.
 *
 * Only three things write it: the probe below, the API client's response
 * interceptor (`#lib/api/index.ts`, which sees every status), and the SSE
 * handshake. A single failed request never flips it on its own — it asks the
 * probe for a verdict instead, so one slow endpoint can't take the app offline.
 */

const HEALTH_URL = `${PUBLIC_API_URL}/debug/health`;
const PROBE_TIMEOUT_MS = 3000;

// A failed probe while the device still reports a network is not trusted on its
// own: on mobile, foregrounding a backgrounded app fires the first probe before
// the radio has finished waking, so it fails transiently while the connection is
// about to succeed. Alarming on it flashes the offline banner for a few seconds.
// So a probe that would take us *offline* keeps re-trying for this long first,
// and only a failure across the whole window counts — the transient-fault
// "let it self-correct before alarming" rule. `navigator.onLine === false`, by
// contrast, is a trustworthy negative and skips the window.
const OFFLINE_CONFIRM_WINDOW_MS = 5000;
// Gap between confirm re-tries. Kept short so a genuine recovery is noticed
// almost as soon as the network returns; each attempt carries its own timeout.
const OFFLINE_CONFIRM_GAP_MS = 500;

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

/**
 * Whether an API call's outcome means the backend wasn't reached: no response at
 * all (network failure, timeout, abort) or a gateway status. Lets a `load` pick
 * its offline state without deciding app-wide reachability itself.
 */
export function isUnreachableResponse(response: Response | undefined): boolean {
	return response === undefined || isBackendUnreachableStatus(response.status);
}

// Optimistic default so the very first paint still attempts the network; the
// first probe corrects it within PROBE_TIMEOUT_MS.
let reachable = true;
// Bumped on every change, so a probe can tell that a fresher verdict landed
// while it was still in flight (see probeReachability).
let version = 0;
const listeners = new Set<() => void>();

/** Last known reachability. */
export function isReachable(): boolean {
	return reachable;
}

/** Update reachability from a known outcome (an HTTP response, the SSE handshake). */
export function markReachable(value: boolean): void {
	if (reachable === value) return;
	reachable = value;
	version += 1;
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
 * Device-level connectivity (`navigator.onLine`).
 *
 * Unlike `reachable` (a server probe), this only says whether a network
 * interface exists — it reports online on a captive portal or dead VPN. Reading
 * it alongside `current` lets the UI tell "the device has no internet" apart
 * from "the device is online but the server can't be reached", so an outage is
 * never miscast as the user's connection dropping. A `false` here is a
 * trustworthy negative (the device really is offline); a `true` is not.
 */
export function deviceOnlineNow(): boolean {
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

function delay(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * One request to the health endpoint. A real CORS request (default mode) — not
 * `no-cors` — so the response is non-opaque and only succeeds when the *backend*
 * answers: in prod the API is same-origin; in dev the backend returns the
 * frontend's `Access-Control-Allow-Origin`. A captive portal intercepting the
 * request serves its own page *without* our CORS header, so the browser rejects
 * it and we correctly fall offline (an opaque `no-cors` probe would wrongly
 * accept it). A gateway status means the proxy answered for a dead backend; any
 * other status, even a 5xx, means the server responded.
 */
async function pingHealth(): Promise<boolean> {
	try {
		const response = await fetch(HEALTH_URL, {
			method: 'GET',
			cache: 'no-store',
			signal: timeoutSignal(PROBE_TIMEOUT_MS)
		});
		return !isBackendUnreachableStatus(response.status);
	} catch {
		return false;
	}
}

// Ping until one answer arrives or there's no reason left to keep trying. Only a
// would-be downgrade (currently reachable, device still has a network) earns the
// confirm window; a recovery check while already offline is a single attempt.
// Fresher evidence landing meanwhile ends it early: its verdict would be dropped.
async function runProbe(startVersion: number): Promise<boolean> {
	const deadline = Date.now() + OFFLINE_CONFIRM_WINDOW_MS;
	for (;;) {
		if (await pingHealth()) return true;

		const confirming =
			version === startVersion && reachable && deviceOnlineNow() && Date.now() < deadline;
		if (!confirming) return false;
		await delay(OFFLINE_CONFIRM_GAP_MS);
	}
}

let inflight: Promise<boolean> | null = null;

/**
 * Probe the health endpoint and record the verdict. Concurrent calls share one
 * probe. A verdict is dropped when a fresher one landed meanwhile — e.g. an API
 * response proved the server reachable while a confirm window was still
 * re-trying — so a slow probe can never overwrite newer evidence.
 */
export function probeReachability(): Promise<boolean> {
	if (inflight) return inflight;

	const startVersion = version;
	inflight = runProbe(startVersion)
		.then((ok) => {
			if (version === startVersion) markReachable(ok);
			return ok;
		})
		.finally(() => {
			inflight = null;
		});

	return inflight;
}
