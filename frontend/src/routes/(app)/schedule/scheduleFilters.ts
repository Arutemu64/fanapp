export interface ScheduleFilters {
	search: string;
	onlySubscribed: boolean;
}

export function parseScheduleFilters(params: Pick<URLSearchParams, 'get'>): ScheduleFilters {
	return {
		search: params.get('q')?.trim() ?? '',
		onlySubscribed: params.get('scope') === 'mine'
	};
}

export function buildScheduleFiltersQuery(filters: ScheduleFilters): string {
	const params = new URLSearchParams();
	const search = filters.search.trim();
	if (search) {
		params.set('q', search);
	}
	if (filters.onlySubscribed) {
		params.set('scope', 'mine');
	}
	const query = params.toString();
	return query ? `?${query}` : '';
}
