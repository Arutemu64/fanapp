import type { PageLoad } from './$types';

// The schedule itself is a TanStack query owned by the page component (persisted
// under the universal scope, so it reads offline) — this load only names the page
// for the app shell's title.
export const load: PageLoad = () => {
	return { title: 'Программа' };
};
