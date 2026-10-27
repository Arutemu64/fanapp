export type NavTransition = 'forward' | 'back' | 'fade';

interface NavTransitionInput {
	from: string;
	to: string;
	fromBackHref: string | undefined;
	tabRoots: ReadonlySet<string>;
}

function depth(pathname: string): number {
	return pathname.split('/').filter(Boolean).length;
}

export function navTransitionKind({
	from,
	to,
	fromBackHref,
	tabRoots
}: NavTransitionInput): NavTransition | null {
	if (from === to) return null;
	if (fromBackHref === to) return 'back';
	if (tabRoots.has(from) && tabRoots.has(to)) return 'fade';

	const fromDepth = depth(from);
	const toDepth = depth(to);
	if (toDepth > fromDepth) return 'forward';
	if (toDepth < fromDepth) return 'back';
	return 'fade';
}
