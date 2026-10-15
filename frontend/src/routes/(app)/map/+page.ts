import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

// Static page; load only supplies the navbar title.
export const load: PageLoad = () => {
	return {
		title: m.nav_map()
	};
};
