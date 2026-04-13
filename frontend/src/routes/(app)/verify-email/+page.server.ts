import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	return {
		status: 'error' as const,
		errorMessage: 'Запросите OTP-код в разделе безопасности профиля и введите его там.'
	};
};
