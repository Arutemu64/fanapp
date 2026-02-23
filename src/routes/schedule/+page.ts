import { client } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const { data, error, response } = await client.GET('/schedule', { fetch });

	if (error) {
		console.error('Error fetching schedule:', error);
		return {
			schedule: []
		};
	}

	return {
		schedule: data?.schedule ?? []
	};
};
