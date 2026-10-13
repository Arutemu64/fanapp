import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { getApiErrorCode, throwApiError } from '#lib/api/errors.js';
import { getUserOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { canReadUsers } from '#lib/utils/permissions.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent, params }) => {
	const { queryClient, user } = await parent();

	// Mirror the backend users:read check before hitting the API, so the page is
	// not shown to users the endpoint would reject with a 403.
	if (!canReadUsers(user)) {
		error(403, 'У тебя нет доступа к карточкам пользователей');
	}

	const data = await queryClient
		.query(getUserOptions({ path: { user_id: params.id } }))
		.catch((apiError: unknown) => {
			if (getApiErrorCode(apiError) === 'USER_NOT_FOUND') {
				error(404, 'Пользователь не найден');
			}
			return throwApiError(apiError, undefined, 'Не удалось загрузить пользователя');
		});

	return {
		title: 'Пользователь',
		back: { href: 'tools/users', label: 'Назад к пользователям' } satisfies BackTarget,
		profile: data
	};
};
