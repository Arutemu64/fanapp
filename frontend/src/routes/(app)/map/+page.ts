import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

// Static page; load only supplies the navbar title, which matches the tab label as
// on every other tab.
export const load: PageLoad = () => {
	return { title: m.nav_map() };
};
