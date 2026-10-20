import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { guideArticles } from '#lib/data/guideArticles.js';
import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

export const load: PageLoad = ({ params }) => {
	const article = guideArticles.find((candidate) => candidate.slug === params.slug);
	if (!article) {
		error(404);
	}
	return {
		article,
		title: article.title,
		// The articles are listed on Home, so that is where the back arrow leads.
		back: { href: '', label: m.common_to_home() } satisfies BackTarget
	};
};
