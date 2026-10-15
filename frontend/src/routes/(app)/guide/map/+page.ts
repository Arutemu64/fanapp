import type { BackTarget } from '#lib/types/navigation.js';

import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

// Static page; load only supplies the navbar title and back target.
export const load: PageLoad = () => {
	return {
		title: m.nav_map(),
		back: { href: 'guide', label: m.guide_back() } satisfies BackTarget
	};
};
