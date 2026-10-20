import { resolve } from '$app/paths';
import { redirect } from '@sveltejs/kit';

import type { PageLoad } from './$types';

// The guide's hub is Home's lower half and its articles sit one level below it, so
// /guide has no page of its own; a bookmark or a shared link to it lands on Home.
export const load: PageLoad = () => {
	redirect(308, resolve(''));
};
