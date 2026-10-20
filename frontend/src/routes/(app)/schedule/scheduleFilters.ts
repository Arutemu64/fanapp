export interface ScheduleFilters {
	search: string;
	onlySubscribed: boolean;
}

// The filters live in the URL so they survive a reload, the back button and a return
// by the Программа tab (which reopens the tab's last query), and so the offset the
// shell restores belongs to the same list. Anything unrecognised reads as "no filter":
// a hand-edited link should still open the programme.
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
	// A word rather than a flag, so a shared link reads as what it shows.
	if (filters.onlySubscribed) {
		params.set('scope', 'mine');
	}
	const query = params.toString();
	return query ? `?${query}` : '';
}
