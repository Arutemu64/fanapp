import { getPublicConfigOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	// The hero's date and start time read the public config; fetch it as early as
	// the route is preloaded, like Home does, and render the cached copy meanwhile.
	const { queryClient } = await parent();
	void queryClient.query(getPublicConfigOptions()).catch(() => {});

	return { title: m.nav_guide() };
};
