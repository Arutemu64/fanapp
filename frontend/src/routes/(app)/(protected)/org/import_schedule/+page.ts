import type { PageLoad } from './$types';

// Static page; load only supplies the navbar title.
export const load: PageLoad = () => {
	return {
		title: 'Импорт расписания'
	};
};
