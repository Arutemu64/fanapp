import { createApiClient } from '$lib/api';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ fetch }) => {
	const client = createApiClient();
	const { data, error } = await client.GET('/voting/status', { fetch });

	if (error) {
		console.error('Error fetching voting status:', error);
		return {
			votingStatus: undefined
		};
	}

	return {
		votingStatus: data
	};
};
