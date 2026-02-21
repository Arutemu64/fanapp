import { api } from '$lib/api';
import type { GetScheduleResponse, ScheduleEventDTO } from '$lib/types/schedule';

export class ScheduleStore {
	schedule = $state<ScheduleEventDTO[]>([]);

	init(initialData: ScheduleEventDTO[]) {
		this.schedule = initialData;
	}

	async refresh() {
		const res: GetScheduleResponse = await api.get('/schedule');
		this.schedule = res.schedule;
	}
}
