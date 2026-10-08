import type { Path } from '$app/types';
import type { Component } from 'svelte';

import { resolve } from '$app/paths';
import { Calendar, CircleUser, Home, MapPin, ThumbsUp } from '@lucide/svelte';

export interface PrimaryNavItem {
	/** Russian label shown under (bottom nav) or beside (sidebar) the icon. */
	label: string;
	href: Path;
	/** Idle icon; the solid twin replaces it on the active route. */
	outlineIcon: Component;
	/** Filled icon shown when the route is active. */
	solidIcon: Component;
	/**
	 * Other route roots reached from this tab's page, which keep the tab lit so the
	 * bar still says where you are. Profile is the hub for feedback and the org
	 * toolbox, which have no tab of their own.
	 */
	nestedRoots?: Path[];
}

/**
 * The primary destinations, in display order, rendered by both navigation
 * surfaces — AppBottomNav (mobile) and AppSidebar (desktop). Single source of
 * truth so the two can't drift in label, order, icon or route, and so the
 * preserved-scroll roots below stay in step with them.
 */
export const PRIMARY_NAV_ITEMS: PrimaryNavItem[] = [
	{ label: 'Главная', href: '', outlineIcon: Home, solidIcon: Home },
	{
		label: 'Программа',
		href: 'schedule',
		outlineIcon: Calendar,
		solidIcon: Calendar
	},
	// Voting sits before the map so its long "Голосование" label lands in an inner
	// column of the bottom nav, away from rounded screen corners that clip edges.
	{ label: 'Голосование', href: 'voting', outlineIcon: ThumbsUp, solidIcon: ThumbsUp },
	{ label: 'Карта', href: 'map', outlineIcon: MapPin, solidIcon: MapPin },
	// Last, in the thumb's natural reach on the right, as the account tab sits in most
	// tab bars. It is also the hub for everything without a tab of its own (feedback,
	// the org toolbox, theme, logout), which is what lets the shell drop a hamburger.
	{
		label: 'Профиль',
		href: 'profile',
		outlineIcon: CircleUser,
		solidIcon: CircleUser,
		nestedRoots: ['feedback', 'tools']
	}
];

/**
 * Pathnames of the routes whose scroll offset the app shell preserves per tab.
 * Derived from the primary destinations so it can never fall out of sync with them.
 */
export const TAB_ROOTS: ReadonlySet<string> = new Set(
	PRIMARY_NAV_ITEMS.map((item) => resolve(item.href))
);
