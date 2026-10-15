import { resolve } from '$app/paths';
import { redirect } from '@sveltejs/kit';

import type { PageLoad } from './$types';

// Links in posts and notifications still point at /map, and an installed app keeps
// its cached manifest's "Карта" shortcut until the browser refreshes the manifest,
// so the path stays as a redirect to the guide's map.
export const load: PageLoad = () => {
	redirect(308, resolve('guide/map'));
};
