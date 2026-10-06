import type { Pathname } from '$app/types';

/**
 * Where the navbar's back arrow leads. A fixed parent route rather than
 * `history.back()`: a page opened from a push notification or a shared link has
 * no in-app history, so "back" would leave the app or do nothing.
 */
export interface BackTarget {
	href: Pathname;
	/** Accessible name of the icon-only button, e.g. «Назад к инструментам». */
	label: string;
}
