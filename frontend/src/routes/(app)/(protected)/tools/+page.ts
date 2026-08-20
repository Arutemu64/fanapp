import type { PageLoad } from './$types';

// The org gate lives in +layout.ts; this page only names itself for the navbar.
export const load: PageLoad = () => {
	return {
		title: 'Инструменты'
	};
};
