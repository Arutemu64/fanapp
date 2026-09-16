import type { PageLoad } from './$types';

// The feed itself is a TanStack query owned by the page component (persisted
// under the user scope, so it reads offline and is dropped on logout) — this load
// only names the page for the app shell's title.
export const load: PageLoad = () => {
	return { title: 'Уведомления' };
};
