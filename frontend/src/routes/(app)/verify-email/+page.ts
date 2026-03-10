import type { PageLoad } from './$types';
import { createApiClient } from '$lib/api';

export const load: PageLoad = async ({ url, fetch }) => {
    const token = url.searchParams.get('token');

    if (!token) {
        return { status: 'error' as const, errorMessage: 'Токен не найден' };
    }

    const client = createApiClient();
    const { error } = await client.POST('/auth/verify-email', {
        body: { token } as any,
        fetch
    });

    if (error) {
        const errorMessage =
            typeof error.detail === 'string' ? error.detail : 'Недействительный или истекший токен';
        return { status: 'error' as const, errorMessage };
    }

    return { status: 'success' as const, errorMessage: '' };
};
