import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	return {
		status: 'error' as const,
		errorMessage: 'Запроси OTP-код в разделе безопасности профиля и введи его там.'
	};
};
