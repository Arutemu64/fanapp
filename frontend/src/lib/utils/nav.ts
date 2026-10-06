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
	item: { href: string; nestedRoots?: readonly string[] }
): boolean {
	const roots = [item.href, ...(item.nestedRoots ?? [])];
	return roots.some((root) => isActivePath(activeUrl, root));
}
