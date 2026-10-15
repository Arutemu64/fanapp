import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

// The organizer gate lives in +layout.ts; this page only names itself for the navbar.
export const load: PageLoad = () => {
	return {
		title: m.tools_title()
	};
};
