import type { LayoutLoad } from './$types';

// Voting status is read by the layout component (and shared with the pages below
// through the query cache), not here: it is an online-only, uncached surface with
// nothing for a `load` to decide — a failed read simply hides the banner.
export const load: LayoutLoad = () => {
	return { title: 'Голосование' };
};
