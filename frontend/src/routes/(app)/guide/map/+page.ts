import { resolve } from '$app/paths';
import { redirect } from '@sveltejs/kit';

import type { PageLoad } from './$types';

// The map has its own tab now. Installed apps keep the manifest they were installed
// with, so their «Карта» shortcut still opens /guide/map until the browser refreshes it.
export const load: PageLoad = () => {
	redirect(308, resolve('map'));
};
