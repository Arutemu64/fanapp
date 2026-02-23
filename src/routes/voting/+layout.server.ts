import createClient from 'openapi-fetch';
import type { paths } from '$lib/api/v1';
import { PRIVATE_API_URL } from '$env/static/private';
import type { LayoutServerLoad } from './$types';

const serverClient = createClient<paths>({
	baseUrl: PRIVATE_API_URL,
	credentials: 'include'
});

export const load: LayoutServerLoad = async ({ fetch }) => {
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
