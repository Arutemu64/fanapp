import { createApiClient } from '$lib/api';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ fetch }) => {
	const serverClient = createApiClient();
	const { data, error } = await serverClient.GET('/voting/status', { fetch });

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
