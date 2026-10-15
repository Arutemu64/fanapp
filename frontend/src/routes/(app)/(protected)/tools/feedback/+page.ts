import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { canReadFeedback } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();

	// The tools layout already gates the section to organizers; mirror the backend
	// FEEDBACK_READ check here so a user without the grant isn't shown a page the
	// list request would reject.
	if (!canReadFeedback(user)) {
		error(403, 'У тебя нет доступа к отзывам');
	}

	return {
		title: 'Отзывы',
		back: { href: 'tools', label: 'Назад к инструментам' } satisfies BackTarget
	};
};
