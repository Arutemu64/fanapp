import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals, depends }) => {
	depends('app:current-user');

	return {
		user: locals.user // expose user to client
	};
};
