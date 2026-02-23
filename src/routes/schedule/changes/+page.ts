import { client } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const { data, error, response } = await client.GET('/schedule/changes', {
		fetch
	});

	if (error || response.status !== 200) {
		return {
			schedule_changes: []
		};
	}

	return {
		schedule_changes: data?.schedule_changes ?? []
	};
};
