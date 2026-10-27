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
	label: () => string;
	href: Path;
	outlineIcon: Component;
	solidIcon: Component;
	nestedRoots?: Path[];
}

export const PRIMARY_NAV_ITEMS: PrimaryNavItem[] = [
	{
		label: m.nav_home,
		href: '',
		outlineIcon: House,
		solidIcon: House,
		nestedRoots: ['guide' as Path]
	},
	{
		label: m.nav_schedule,
		href: 'schedule',
		outlineIcon: Calendar,
		solidIcon: Calendar
	},
	{ label: m.nav_map, href: 'map', outlineIcon: MapIcon, solidIcon: MapIcon },
	{ label: m.nav_voting, href: 'voting', outlineIcon: ThumbsUp, solidIcon: ThumbsUp },
	{
		label: m.nav_profile,
		href: 'profile',
		outlineIcon: CircleUser,
		solidIcon: CircleUser,
		nestedRoots: ['feedback', 'tools']
	}
];

export const TAB_ROOTS: ReadonlySet<string> = new Set(
	PRIMARY_NAV_ITEMS.map((item) => resolvePath(item.href))
);
