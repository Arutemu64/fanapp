import { redirect } from '@sveltejs/kit';
import type { LayoutLoad, LayoutLoadEvent } from './$types';

export const load: LayoutLoad = async ({ parent }: LayoutLoadEvent) => {
	// Reuse the user from the root layout data so this guard works
	// for both the first SSR render and later client-side navigations.
	const { user } = await parent();

	if (user) {
		redirect(303, '/');
	}

	return {};
};