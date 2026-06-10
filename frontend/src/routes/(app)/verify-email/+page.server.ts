import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	return {
		errorMessage: 'Запроси OTP-код в разделе безопасности профиля и введи его там.'
	};
};
