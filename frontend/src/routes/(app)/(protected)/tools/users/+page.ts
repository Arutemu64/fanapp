import { throwApiError } from '$lib/api/errors';
import { listUsersOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
import { USERS_PAGE_SIZE } from '$lib/constants/users';
import { canReadUsers } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent, url }) => {
	const { queryClient, user } = await parent();

	// The tools layout gates the section to organisers; mirror the backend
	// users:read check here so a user without the grant isn't shown a page the
	// list request would reject with a 403.
	if (!canReadUsers(user)) {
		error(403, 'У тебя нет доступа к списку пользователей');
	}

	// Page and search live in the URL so results are shareable and survive the
	// back button; the server owns pagination and search, so every change is a
	// fresh request rather than client-side filtering of a partial list. Both ride
	// in the query key, so each page/search combination caches separately.
	const search = url.searchParams.get('q')?.trim() ?? '';
	const rawPage = Number(url.searchParams.get('page'));
	const page = Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1;

	const query = {
		limit: USERS_PAGE_SIZE,
		offset: (page - 1) * USERS_PAGE_SIZE,
		...(search ? { search } : {})
	};

	// Awaited: this page seeds its form/table state from the response at mount, so
	// it must be in the cache before the component runs. A failure here is a real
	// server error — the tools layout already redirects offline visitors to the hub
	// — so it becomes the error page rather than an inline state.
	await queryClient.ensureQueryData(listUsersOptions({ query })).catch((requestError: unknown) => {
		throwApiError(requestError, undefined, 'Не удалось загрузить пользователей');
	});

	return { page, query, search, title: 'Пользователи' };
};
