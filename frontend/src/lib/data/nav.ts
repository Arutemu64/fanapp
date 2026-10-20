import type { Path } from '$app/types';
import type { Component } from 'svelte';

import Calendar from '@lucide/svelte/icons/calendar';
import CircleUser from '@lucide/svelte/icons/circle-user';
import House from '@lucide/svelte/icons/house';
import MapIcon from '@lucide/svelte/icons/map';
import ThumbsUp from '@lucide/svelte/icons/thumbs-up';

import { m } from '#lib/paraglide/messages.js';
import { resolvePath } from '#lib/utils/paths.js';

export interface PrimaryNavItem {
	/** Russian label shown under (bottom nav) or beside (sidebar) the icon. */
	label: () => string;
	href: Path;
	/** Idle icon; the solid twin replaces it on the active route. */
	outlineIcon: Component;
	/** Filled icon shown when the route is active. */
	solidIcon: Component;
	/**
	 * Other route roots reached from this tab's page, which keep the tab lit so the
	 * bar still says where you are. Home lists the guide articles, and Profile is the
	 * hub for feedback and the organizer toolbox, none of which have a tab of their own.
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
	{
		label: m.nav_home,
		href: '',
		outlineIcon: House,
		solidIcon: House,
		// /guide has no page of its own, only the articles under it, so the bare root
		// isn't a `Path`; resolving it is still a plain prefix match.
		nestedRoots: ['guide' as Path]
	},
	{
		label: m.nav_schedule,
		href: 'schedule',
		outlineIcon: Calendar,
		solidIcon: Calendar
	},
	// The map takes the centre of the bar, the most prominent spot, as the tab people
	// on site reach for most. Voting stays in an inner column, since its long
	// "Голосование" label would be clipped by the rounded screen corners at an edge.
	{ label: m.nav_map, href: 'map', outlineIcon: MapIcon, solidIcon: MapIcon },
	{ label: m.nav_voting, href: 'voting', outlineIcon: ThumbsUp, solidIcon: ThumbsUp },
	// Last, in the thumb's natural reach on the right, as the account tab sits in most
	// tab bars. It is also the hub for everything without a tab of its own (feedback,
	// the organizer toolbox, theme, logout), which is what lets the shell drop a hamburger.
	{
		label: m.nav_profile,
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
	PRIMARY_NAV_ITEMS.map((item) => resolvePath(item.href))
);
