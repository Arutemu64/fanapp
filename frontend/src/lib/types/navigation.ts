import type { Path } from '$app/types';
import type { Component } from 'svelte';

/**
 * Where the navbar's back arrow leads. A fixed parent route rather than
 * `history.back()`: a page opened from a push notification or a shared link has
 * no in-app history, so "back" would leave the app or do nothing.
 */
export interface BackTarget {
	href: Path;
	/** Accessible name of the icon-only button, e.g. «Назад к инструментам». */
	label: string;
}

/**
 * An icon button a page adds to the navbar, beside the bell. For page-level
 * actions (e.g. the organiser's change log on the schedule), not in-content
 * controls. Keep it to two per page: with the bell that is the three trailing
 * icons a phone top bar holds before an overflow menu is needed
 * (https://www.sap.com/design-system/fiori-design-android/v26-4/components/navigation-and-search/top-app-bar/usage).
 */
export interface NavbarAction {
	href: Path;
	/** Accessible name of the icon-only button, e.g. «Изменения программы». */
	label: string;
	icon: Component;
}
