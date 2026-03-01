import type { PageLoad } from './$types';
import { client } from '$lib/api';

export const load: PageLoad = async ({ fetch }) => {
    const { data: pushSubscriptions } = await client.GET('/push', { fetch });

    return {
        pushSubscriptions: pushSubscriptions ?? []
    };
};
