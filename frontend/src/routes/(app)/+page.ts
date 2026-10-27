import {
	getPublicConfigOptions,
	getScheduleOptions,
	getVotingStatusOptions
} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient } = await parent();
	void queryClient.query(getPublicConfigOptions()).catch(() => {});
	void queryClient.query(getScheduleOptions()).catch(() => {});
	void queryClient.query(getVotingStatusOptions()).catch(() => {});

	return { title: m.nav_home() };
};
