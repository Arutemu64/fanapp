import { api, client } from '$lib/api';
import type { GetScheduleResponse } from '$lib/types/schedule';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const test = await client.GET("/api/schedule", {fetch});
	const data = test.data;
	const schedule = data?.schedule;
	const res: GetScheduleResponse = await api.get('/schedule', { customFetch: fetch });
	return {
		schedule: schedule ?? []
	};
};
