import { api } from '$lib/api';
import type { ListScheduleChangesResponse } from '$lib/types/schedule';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const res: ListScheduleChangesResponse = await api.get('/schedule/changes', { customFetch: fetch });
	return {
		schedule_changes: res.schedule_changes
	};
};