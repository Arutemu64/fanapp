import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { throwApiError } from '#lib/api/errors.js';
import { listUsersOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { USERS_PAGE_SIZE } from '#lib/constants/users.js';
import { canReadUsers } from '#lib/utils/permissions.js';

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
	// fresh request rather than client-side filtering of a partial list.
	const search = url.searchParams.get('q')?.trim() ?? '';
	const rawPage = Number(url.searchParams.get('page'));
	const page = Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1;
	const offset = (page - 1) * USERS_PAGE_SIZE;

	// Staff-only operational directory: stale data would misrepresent live state,
	// so it waits for a fresh page rather than serving a cached one.
	const data = await queryClient
		.query({
			...listUsersOptions({
				query: { limit: USERS_PAGE_SIZE, offset, ...(search ? { search } : {}) }
			}),
			staleTime: 0
		})
		.catch((apiError: unknown) =>
			throwApiError(apiError, undefined, 'Не удалось загрузить пользователей')
		);

	return {
		title: 'Пользователи',
		back: { href: 'tools', label: 'Назад к инструментам' } satisfies BackTarget,
		users: data.users,
		total: data.total,
		page,
		search
	};
};
