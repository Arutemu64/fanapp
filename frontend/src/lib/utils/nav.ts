import type { Path } from '$app/types';

import { resolvePath } from '#lib/utils/paths.js';

export function isActivePath(activeUrl: string, href: string): boolean {
	if (href === '/') return activeUrl === '/';
	return activeUrl === href || activeUrl.startsWith(href + '/');
}

export function isNavItemActive(
	activeUrl: string,
	item: { href: Path; nestedRoots?: readonly Path[] }
): boolean {
	const roots = [item.href, ...(item.nestedRoots ?? [])];
	return roots.some((root) => isActivePath(activeUrl, resolvePath(root)));
}

export function tabHref(href: Path, lastSearches: Readonly<Record<string, string>>): string {
	const root = resolvePath(href);
	return `${root}${lastSearches[root] ?? ''}`;
}

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

export function hasUpdateDot(href: Path, updateAvailable: boolean): boolean {
	return href === 'profile' && updateAvailable;
}

export function toAppPath(backendPath: string): Path {
	return backendPath.replace(/^\//, '') as Path;
}
