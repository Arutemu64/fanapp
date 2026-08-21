import type { Component } from 'svelte';

import {
	CalendarWeekOutline,
	CalendarWeekSolid,
	HomeOutline,
	HomeSolid,
	MapPinAltOutline,
	MapPinAltSolid,
	ThumbsUpOutline,
	ThumbsUpSolid
} from 'flowbite-svelte-icons';

export interface PrimaryNavItem {
	/** Russian label shown under (bottom nav) or beside (sidebar) the icon. */
	label: string;
	href: string;
	/** Idle icon; the solid twin replaces it on the active route. */
	outlineIcon: Component;
	/** Filled icon shown when the route is active. */
	solidIcon: Component;
}

/**
 * The primary destinations, in display order, rendered by both navigation
 * surfaces — AppBottomNav (mobile) and AppSidebar (desktop). Single source of
 * truth so the two can't drift in label, order, icon or route, and so the
 * preserved-scroll roots below stay in step with them.
 */
export const PRIMARY_NAV_ITEMS: PrimaryNavItem[] = [
	{ label: 'Главная', href: '/', outlineIcon: HomeOutline, solidIcon: HomeSolid },
	{
		label: 'Программа',
		href: '/schedule',
		outlineIcon: CalendarWeekOutline,
		solidIcon: CalendarWeekSolid
	},
	// Voting sits before the map so its long "Голосование" label lands in an inner
	// column of the bottom nav, away from rounded screen corners that clip edges.
	{ label: 'Голосование', href: '/voting', outlineIcon: ThumbsUpOutline, solidIcon: ThumbsUpSolid },
	{ label: 'Карта', href: '/map', outlineIcon: MapPinAltOutline, solidIcon: MapPinAltSolid }
];

/**
 * Routes whose scroll offset the app shell preserves per tab. Derived from the
 * primary destinations so it can never fall out of sync with them.
 */
export const TAB_ROOTS = new Set(PRIMARY_NAV_ITEMS.map((item) => item.href));
