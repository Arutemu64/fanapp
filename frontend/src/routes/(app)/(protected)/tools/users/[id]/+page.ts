import { throwQueryError } from '$lib/api/errors';
import { getUserOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
import { canReadUsers } from '$lib/utils/permissions';
import { error } from '@sveltejs/kit';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent, params }) => {
	const { queryClient, user } = await parent();

	// Mirror the backend users:read check before hitting the API, so the page is
	// not shown to users the endpoint would reject with a 403.
	if (!canReadUsers(user)) {
		error(403, 'У тебя нет доступа к карточкам пользователей');
	}

	// The title needs the loaded profile, so this one keeps the resolved value —
	// the component reads the same cache entry.
	try {
		const profile = await queryClient.ensureQueryData(
			getUserOptions({ path: { user_id: params.id } })
		);
		return { title: profile.username };
	} catch (requestError) {
		throwQueryError(requestError, 'Не удалось загрузить пользователя');
	}
};
