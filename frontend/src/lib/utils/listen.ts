import { onDestroy } from 'svelte';

/**
 * Attach a DOM event listener that removes itself when the surrounding component
 * is destroyed, so callers don't have to mirror every `addEventListener` with a
 * matching `removeEventListener` in a teardown method.
 *
 * Must be called during component initialization — e.g. from the constructor of
 * a service that a layout instantiates in its `<script>` — because it registers
 * the cleanup via Svelte's `onDestroy`. The returned function removes the
 * listener early if a caller needs to.
 *
 * A service that owns global listeners uses this instead of `<svelte:window>` /
 * `<svelte:document>` so the wiring stays with the service (self-contained and
 * testable), not spread across the layout markup.
 */
export function listen<K extends keyof WindowEventMap>(
	target: Window,
	type: K,
	handler: (event: WindowEventMap[K]) => void,
	options?: boolean | AddEventListenerOptions
): () => void;
export function listen<K extends keyof DocumentEventMap>(
	target: Document,
	type: K,
	handler: (event: DocumentEventMap[K]) => void,
	options?: boolean | AddEventListenerOptions
): () => void;
export function listen(
	target: EventTarget,
	type: string,
	handler: EventListenerOrEventListenerObject,
	options?: boolean | AddEventListenerOptions
): () => void {
	target.addEventListener(type, handler, options);
	const off = () => target.removeEventListener(type, handler, options);
	onDestroy(off);
	return off;
}
