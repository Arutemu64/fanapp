import { ref } from 'vue';

/**
 * Wall-clock time as a *reactive* read that ticks once a minute, for relative
 * labels ("5 минут назад") that would otherwise freeze at first render while an
 * installed app stays open for hours.
 *
 * Module-global like `documentVisibility`: the time is a device fact, not user-
 * or session-scoped state. One interval is shared by every reader. It starts on
 * the first read, so nothing ticks until a screen actually shows a relative
 * label, and then runs for the life of the page.
 */
const MINUTE_MS = 60_000;

const nowMs = ref(Date.now());
let ticking = false;

function startTicking(): void {
	if (ticking) return;
	ticking = true;
	// Refresh after the current read, not during it: writing a ref from inside a
	// computed that is reading it would re-trigger that computed mid-evaluation.
	queueMicrotask(() => {
		nowMs.value = Date.now();
	});
	setInterval(() => {
		nowMs.value = Date.now();
	}, MINUTE_MS);
}

export const minuteClock = {
	get now(): number {
		startTicking();
		return nowMs.value;
	}
};
