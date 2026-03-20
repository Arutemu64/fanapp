import type { PageServerLoad } from './$types';
import { createApiClient } from '$lib/api';

const INVALID_TOKEN_MESSAGE = 'Недействительная или устаревшая ссылка подтверждения';

export const load: PageServerLoad = async ({ url, fetch }) => {
	const token = url.searchParams.get('token');

	if (!token) {
		return { status: 'error' as const, errorMessage: 'Токен не найден' };
	}

	const client = createApiClient();
	const { error, response } = await client.POST('/auth/verify-email', {
		// Выполняем подтверждение только на сервере,
		// чтобы одноразовый токен не расходовался повторно при гидратации.
		body: { token },
		fetch
	});

	if (error) {
		// Логируем техническую информацию на сервере,
		// а пользователю показываем безопасное и понятное сообщение.
		console.error('Verify email error:', response.status, response.statusText);

		return {
			status: 'error' as const,
			errorMessage: INVALID_TOKEN_MESSAGE
		};
	}

	return { status: 'success' as const, errorMessage: '' };
};