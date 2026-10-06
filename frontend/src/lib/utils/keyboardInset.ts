/** The parts of `window.visualViewport` the inset is computed from. */
export interface VisualViewportSize {
	height: number;
	offsetTop: number;
	scale: number;
}

/**
 * How many CSS pixels at the bottom of the layout viewport an on-screen keyboard
 * covers. Mobile Safari (and Chrome's default `resizes-visual`) shrink only the
 * visual viewport when the keyboard opens, so a `position: fixed; bottom: 0`
 * sheet keeps its place behind it; `interactive-widget=resizes-content` would fix
 * that in Chrome but no Safari version supports it
 * (https://caniuse.com/mdn-html_elements_meta_name_viewport_interactive-widget).
 *
 * The covered strip is what lies below the visual viewport's bottom edge:
 * layout height − (visual top offset + visual height). A pinch-zoom shrinks the
 * visual viewport too, so a scaled viewport reports no inset rather than padding
 * a sheet for a keyboard that isn't there.
 */
export function keyboardInset(layoutHeight: number, visual: VisualViewportSize): number {
	if (Math.abs(visual.scale - 1) > 0.01) {
		return 0;
	}
	const covered = layoutHeight - visual.offsetTop - visual.height;
	return Math.max(0, Math.round(covered));
}
