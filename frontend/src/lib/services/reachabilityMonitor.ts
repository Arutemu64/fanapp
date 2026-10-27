import { onlineManager } from '@tanstack/svelte-query';

import { isReachable, markReachable, onReachableChange, probeReachability } from './reachability';

const RECOVERY_POLL_MIN_MS = 3000;
const RECOVERY_POLL_MAX_MS = 30000;

export function startReachabilityMonitor({ onRecovered }: { onRecovered: () => void }): () => void {
	let pollTimerId: ReturnType<typeof setTimeout> | null = null;
	let pollDelayMs = RECOVERY_POLL_MIN_MS;

	function schedulePoll() {
		pollTimerId = setTimeout(() => {
			void (async () => {
				await probeReachability();
				if (pollTimerId === null || isReachable()) return;
				pollDelayMs = Math.min(pollDelayMs * 2, RECOVERY_POLL_MAX_MS);
				schedulePoll();
			})();
		}, pollDelayMs);
	}

	function startPolling() {
		if (pollTimerId !== null) return;
		pollDelayMs = RECOVERY_POLL_MIN_MS;
		schedulePoll();
	}

	function stopPolling() {
		if (pollTimerId === null) return;
		clearTimeout(pollTimerId);
		pollTimerId = null;
	}

	const unsubscribe = onReachableChange(() => {
		if (!isReachable()) {
			startPolling();
			return;
		}

		stopPolling();
		onRecovered();
	});

	onlineManager.setEventListener((setOnline) => {
		setOnline(isReachable());
		return onReachableChange(() => setOnline(isReachable()));
	});

	const handleOffline = () => markReachable(false);
	const handleOnline = () => void probeReachability();
	const handleVisibilityChange = () => {
		if (document.visibilityState === 'visible') void probeReachability();
	};
	window.addEventListener('offline', handleOffline);
	window.addEventListener('online', handleOnline);
	document.addEventListener('visibilitychange', handleVisibilityChange);

	if (!isReachable()) startPolling();
	void probeReachability();

	return () => {
		unsubscribe();
		stopPolling();
		window.removeEventListener('offline', handleOffline);
		window.removeEventListener('online', handleOnline);
		document.removeEventListener('visibilitychange', handleVisibilityChange);
	};
}
