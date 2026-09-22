import { throwApiError } from '$lib/api/errors';
import { getUserOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
import { canReadUsers } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, parent }) => {
	const { queryClient, user } = await parent();

	// Mirror the backend users:read check before hitting the API, so the page is
	// not shown to users the endpoint would reject with a 403.
	if (!canReadUsers(user)) {
		error(403, 'У тебя нет доступа к карточкам пользователей');
	}

	// Awaited because the navbar heading is this user's name (`page.data.title`)
	// and only the response carries it; the page then reads the same cache entry.
	const profile = await queryClient
		.ensureQueryData(getUserOptions({ path: { user_id: params.id } }))
		.catch((requestError: unknown) => {
			throwApiError(requestError, undefined, 'Не удалось загрузить пользователя');
		});

	return {
		title: profile.username,
		userId: params.id
	};
};
