export type FestivalPhase = 'before' | 'during' | 'after';

export function getFestivalPhase(now: number, startMs: number, endMs: number): FestivalPhase {
	if (now >= endMs) return 'after';
	if (now >= startMs) return 'during';
	return 'before';
}

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
