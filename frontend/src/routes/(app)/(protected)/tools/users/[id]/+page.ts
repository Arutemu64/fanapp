import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { canReadUsers } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, parent, params }) => {
	const { user } = await parent();

	// Mirror the backend users:read check before hitting the API, so the page is
	// not shown to users the endpoint would reject with a 403.
	if (!canReadUsers(user)) {
		error(403, 'У тебя нет доступа к карточкам пользователей');
	}

	const client = createApiClient();
	const {
		data,
		error: fetchError,
		response
	} = await client.GET('/users/{user_id}', {
		fetch,
		params: { path: { user_id: params.id } }
	});

	if (response.status === 404) {
		error(404, 'Пользователь не найден');
	}
	if (fetchError || !data) {
		throwApiError(fetchError, response, 'Не удалось загрузить пользователя');
	}

	return {
		title: data.username,
		profile: data
	};
};
