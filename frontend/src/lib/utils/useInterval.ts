import { onDestroy } from 'svelte';

/**
 * A self-clearing `setInterval`: runs `callback` every `delayMs` while started,
 * and cancels itself when the surrounding component is destroyed — so a timer
 * kicked off in a component's script can never outlive it (docs/frontend.md §5).
 *
 * Must be created during component initialization (it registers `onDestroy`) —
 * e.g. from the constructor of a class a component instantiates in its
 * `<script>`. Mirrors `listen.ts`: the teardown wiring lives with the helper,
 * so a caller can't forget the matching `clearInterval`. `start()` restarts a
 * running timer rather than stacking a second one.
 */
export interface Interval {
	start(): void;
	stop(): void;
}

export function useInterval(callback: () => void, delayMs: number): Interval {
	let id: ReturnType<typeof setInterval> | undefined;

	function stop(): void {
		clearInterval(id);
		id = undefined;
	}

	function start(): void {
		stop();
		id = setInterval(callback, delayMs);
	}

	onDestroy(stop);

	return { start, stop };
}
