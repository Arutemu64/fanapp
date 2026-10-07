export type FestivalPhase = 'before' | 'during' | 'after';

/**
 * Both boundaries are instants, so the phase flips on its own as the clock
 * crosses them — there is no operator switch to forget to press.
 */
export function getFestivalPhase(now: number, startMs: number, endMs: number): FestivalPhase {
	if (now >= endMs) return 'after';
	if (now >= startMs) return 'during';
	return 'before';
}

/** The earliest of `boundaries` still ahead of `now`, or null; non-finite entries are skipped. */
export function nextBoundary(boundaries: number[], now: number): number | null {
	let next: number | null = null;
	for (const boundary of boundaries) {
		if (!Number.isFinite(boundary) || boundary <= now) continue;
		if (next === null || boundary < next) {
			next = boundary;
		}
	}
	return next;
}
