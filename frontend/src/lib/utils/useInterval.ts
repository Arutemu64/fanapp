import { onDestroy } from 'svelte';

export interface Interval {
	start(): void;
	stop(): void;
}

export function useInterval(callback: () => void, delayMs: number): Interval {
	let id: ReturnType<typeof setInterval> | undefined;
	let destroyed = false;

	function stop(): void {
		clearInterval(id);
		id = undefined;
	}

	function start(): void {
		if (destroyed) return;
		stop();
		id = setInterval(callback, delayMs);
	}

	onDestroy(() => {
		destroyed = true;
		stop();
	});

	return { start, stop };
}
