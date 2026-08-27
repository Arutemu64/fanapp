import { isReachable } from '$lib/services/reachability';

import type { PageLoad } from './$types';

// Feedback is a submit-only surface — there is nothing to read offline. When the
// backend is unreachable, flag it so the page shows an honest online-only state
// instead of a form whose submit is doomed. Mirrors the voting load's pattern.
export const load: PageLoad = () => {
	return {
		title: 'Обратная связь',
		offlineUnavailable: !isReachable()
	};
};
