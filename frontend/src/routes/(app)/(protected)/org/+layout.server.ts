import { error } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals }) => {
	// Блокируем доступ ко всей секции организаторов, если роль пользователя не 'org'
	if (locals.user?.role !== 'org') {
		error(403, 'У тебя нет доступа к разделу организаторов');
	}
};
