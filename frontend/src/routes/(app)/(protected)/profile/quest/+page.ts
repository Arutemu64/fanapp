import { getQuestOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient } = await parent();
	// Start the fetch on hover/tap; the page renders from the query itself.
	void queryClient.query(getQuestOptions()).catch(() => {});
	return { title: m.quest_title() };
};
