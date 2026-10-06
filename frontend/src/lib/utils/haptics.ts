// Long enough to feel as a tick, short enough not to read as a buzz.
const CONFIRM_TICK_MS = 10;

/**
 * A light haptic tick confirming a key action went through (a vote counted, a
 * subscription saved), the way native apps acknowledge one.
 *
 * Android only, by necessity: Safari has never shipped the Vibration API, and the
 * hidden-`<input switch>` trick that faked haptics on iOS stopped working in iOS
 * 26.5 (https://haptics-web.vercel.app/). Gated to touch-first devices, so a desktop
 * Chrome, which exposes `vibrate` with no motor behind it, never calls it at all.
 */
export function confirmHaptic(): void {
	if (!('vibrate' in navigator)) return;
	if (!window.matchMedia('(pointer: coarse)').matches) return;
	navigator.vibrate(CONFIRM_TICK_MS);
}
