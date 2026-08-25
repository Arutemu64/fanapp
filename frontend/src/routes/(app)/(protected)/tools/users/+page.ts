import { createApiClient } from '$lib/api';
import { throwApiError } from '$lib/api/errors';
import { USERS_PAGE_SIZE } from '$lib/constants/users';
import { canReadUsers } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, parent, url }) => {
	const { user } = await parent();

	// The tools layout gates the section to organisers; mirror the backend
	// users:read check here so a user without the grant isn't shown a page the
	// list request would reject with a 403.
	if (!canReadUsers(user)) {
		error(403, 'У тебя нет доступа к списку пользователей');
	}

	// Page and search live in the URL so results are shareable and survive the
	// back button; the server owns pagination and search, so every change is a
	// fresh request rather than client-side filtering of a partial list.
	const search = url.searchParams.get('q')?.trim() ?? '';
	const rawPage = Number(url.searchParams.get('page'));
	const page = Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1;
	const offset = (page - 1) * USERS_PAGE_SIZE;

	const client = createApiClient();

	// Staff-only operational directory: stale data would misrepresent live state,
	// so no offline cache — fail hard when unreachable instead.
	const {
		data,
		error: fetchError,
		response
	} = await client.GET('/users/', {
		fetch,
		params: {
			query: {
				limit: USERS_PAGE_SIZE,
				offset,
				...(search ? { search } : {})
			}
		}
	});
	if (fetchError || !data) {
		throwApiError(fetchError, response, 'Не удалось загрузить пользователей');
	}

	return {
		title: 'Пользователи',
		users: data.users,
		total: data.total,
		page,
		search
	};
};
