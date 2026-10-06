/**
 * Which page transition a navigation between two in-app paths gets, read by the
 * `html[data-nav-transition]` rules in app.css:
 *   - `forward` / `back`: shared-axis slide, for moving down or up the hierarchy;
 *   - `fade`: fade-through, for peers — tab to tab, or two siblings at one depth.
 * Same-path navigations (a query-only change such as a filter) get none.
 */
export type NavTransition = 'forward' | 'back' | 'fade';

interface NavTransitionInput {
	from: string;
	to: string;
	/** The page being left's navbar back target (`page.data.back?.href`). */
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
	// The navbar's back arrow is a plain link (a push, not history.back()), so
	// history direction can't tell "up" apart; the page's declared parent can.
	if (fromBackHref === to) return 'back';
	if (tabRoots.has(from) && tabRoots.has(to)) return 'fade';

	const fromDepth = depth(from);
	const toDepth = depth(to);
	if (toDepth > fromDepth) return 'forward';
	if (toDepth < fromDepth) return 'back';
	return 'fade';
}
