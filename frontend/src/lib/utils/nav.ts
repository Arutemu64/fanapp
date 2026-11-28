import type { Path, ResolvedPathname } from '$app/types';

import { resolvePath } from '#lib/utils/paths.js';

export function isActivePath(activeUrl: string, href: string): boolean {
	if (href === '/') return activeUrl === '/';
	return activeUrl === href || activeUrl.startsWith(`${href}/`);
}

export function navItemCurrent(
	activeUrl: string,
	item: { href: Path; nestedRoots?: readonly Path[] }
): 'page' | 'location' | undefined {
	if (activeUrl === resolvePath(item.href)) return 'page';
	const roots = [item.href, ...(item.nestedRoots ?? [])];
	return roots.some((root) => isActivePath(activeUrl, resolvePath(root))) ? 'location' : undefined;
}

export function tabHref(
	href: Path,
	lastSearches: Readonly<Record<string, string>>
): ResolvedPathname {
	const root = resolvePath(href);
	const search = lastSearches[root];
	return search ? resolvePath(`${href}?${search.slice(1)}`) : root;
}

export function handleNavItemClick(
	event: MouseEvent,
	activeUrl: string,
	href: Path,
	scrollToTop: () => void
): void {
	if (event.button !== 0 || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey)
		return;
	if (activeUrl !== resolvePath(href)) return;
	event.preventDefault();
	scrollToTop();
}

export function hasUpdateDot(href: Path, updateAvailable: boolean): boolean {
	return href === 'profile' && updateAvailable;
}

export function toAppPath(backendPath: string): Path {
	return backendPath.replace(/^\//, '') as Path;
}
