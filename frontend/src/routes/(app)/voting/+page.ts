import { client } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const { data, error } = await client.GET('/voting/nominations', { fetch });

	if (error) {
		console.error('Error fetching nominations:', error);
		return {
			nominations: []
		};
	}

	return {
		nominations: data?.nominations ?? []
	};
};
