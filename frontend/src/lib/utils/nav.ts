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
 * The primary destinations rendered as tabs in both navigation surfaces. The
 * app shell preserves each one's scroll position per tab, so this must mirror
 * the primary hrefs in AppBottomNav and AppSidebar.
 */
export const TAB_ROOTS = new Set(['/', '/schedule', '/voting', '/map']);
