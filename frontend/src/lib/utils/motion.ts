import { browser } from '$app/environment';

const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';

export function prefersReducedMotion() {
	return browser && window.matchMedia(REDUCED_MOTION_QUERY).matches;
}

export function getReducedMotionMediaQuery() {
	return browser ? window.matchMedia(REDUCED_MOTION_QUERY) : null;
}
