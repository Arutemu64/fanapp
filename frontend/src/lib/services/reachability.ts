import { PUBLIC_API_URL } from '$app/env/public';
import { createSubscriber } from 'svelte/reactivity';

import { timeoutSignal } from '#lib/utils/fetchTimeout.js';

const HEALTH_URL = `${PUBLIC_API_URL}/debug/health`;
const PROBE_TIMEOUT_MS = 3000;

const OFFLINE_CONFIRM_WINDOW_MS = 5000;
const OFFLINE_CONFIRM_GAP_MS = 500;

const BACKEND_UNREACHABLE_STATUSES = new Set([502, 503, 504]);

export function isBackendUnreachableStatus(status: number): boolean {
	return BACKEND_UNREACHABLE_STATUSES.has(status);
}

let reachable = true;
let version = 0;
const listeners = new Set<() => void>();

export function isReachable(): boolean {
	return reachable;
}

export function markReachable(value: boolean): void {
	version += 1;
	if (reachable === value) return;
	reachable = value;
	for (const listener of listeners) listener();
}

export function onReachableChange(listener: () => void): () => void {
	listeners.add(listener);
	return () => listeners.delete(listener);
}

const subscribeReachable = createSubscriber((update) => onReachableChange(update));

const subscribeDeviceOnline = createSubscriber((update) => {
	window.addEventListener('online', update);
	window.addEventListener('offline', update);
	return () => {
		window.removeEventListener('online', update);
		window.removeEventListener('offline', update);
	};
});

export const reachability = {
	get current(): boolean {
		subscribeReachable();
		return reachable;
	},
	get deviceOnline(): boolean {
		subscribeDeviceOnline();
		return navigator.onLine;
	}
};

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

async function runProbe(startVersion: number): Promise<boolean> {
	const deadline = Date.now() + OFFLINE_CONFIRM_WINDOW_MS;
	for (;;) {
		if (await pingHealth()) return true;

		const confirming =
			version === startVersion && reachable && navigator.onLine && Date.now() < deadline;
		if (!confirming) return false;
		await new Promise((resolve) => setTimeout(resolve, OFFLINE_CONFIRM_GAP_MS));
	}
}

let inflight: Promise<boolean> | null = null;

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
