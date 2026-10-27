export interface VisualViewportSize {
	height: number;
	offsetTop: number;
	scale: number;
}

export function keyboardInset(layoutHeight: number, visual: VisualViewportSize): number {
	if (Math.abs(visual.scale - 1) > 0.01) {
		return 0;
	}
	const covered = layoutHeight - visual.offsetTop - visual.height;
	return Math.max(0, Math.round(covered));
}
