import type { Path } from '$app/types';

import { resolvePath } from '#lib/utils/paths.js';

/**
 * Shared navigation helpers used by both navigation surfaces (sidebar + bottom nav)
 * so their active-route rules can't drift.
 */

/**
 * Whether `href` is the active route: exact match for "/", prefix match for nested routes.
 */
export function isActivePath(activeUrl: string, href: string): boolean {
	if (href === '/') return activeUrl === '/';
	return activeUrl === href || activeUrl.startsWith(href + '/');
}

/**
 * Whether a navigation item is active: its own route, or one of the routes it is
 * the entry point for (`nestedRoots`).
 */
export function isNavItemActive(
	activeUrl: string,
	item: { href: Path; nestedRoots?: readonly Path[] }
): boolean {
	const roots = [item.href, ...(item.nestedRoots ?? [])];
	return roots.some((root) => isActivePath(activeUrl, resolvePath(root)));
}

/**
 * Re-tapping the tab whose root you're already on returns to the top instead of
 * navigating, the native bottom-bar affordance. Exact match only: from a nested page
 * (active by prefix) the tap should navigate to the root.
 */
export function handleNavItemClick(
	event: MouseEvent,
	activeUrl: string,
	href: Path,
	scrollToTop: () => void
): void {
	if (activeUrl !== resolvePath(href)) return;
	event.preventDefault();
	scrollToTop();
}

/**
 * Whether the item carries the "update available" dot: only Profile does, since the
 * update row lives on that hub.
 */
export function hasUpdateDot(href: Path, updateAvailable: boolean): boolean {
	return href === 'profile' && updateAvailable;
}

/**
 * A backend deep link ("/schedule", "/" for home) as an app `Path`. The API
 * sends root-relative pathnames, but `resolve()` reads a leading "/" as a route
 * ID, whose segments it would parse for [params] and (groups).
 */
export function toAppPath(backendPath: string): Path {
	return backendPath.replace(/^\//, '') as Path;
}
