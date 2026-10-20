import { describe, expect, it } from 'vitest';

import { buildScheduleFiltersQuery, parseScheduleFilters } from './scheduleFilters';

describe('parseScheduleFilters', () => {
	it('reads every filter from the URL', () => {
		const params = new URLSearchParams('q=%20косплей%20&scope=mine');
		expect(parseScheduleFilters(params)).toEqual({ search: 'косплей', onlySubscribed: true });
	});

	it('treats missing or unknown values as no filter', () => {
		const params = new URLSearchParams('scope=everything');
		expect(parseScheduleFilters(params)).toEqual({ search: '', onlySubscribed: false });
	});
});

describe('buildScheduleFiltersQuery', () => {
	it('round-trips through parseScheduleFilters', () => {
		const filters = { search: 'Дефиле 12', onlySubscribed: true };
		const query = buildScheduleFiltersQuery(filters);
		expect(parseScheduleFilters(new URLSearchParams(query))).toEqual(filters);
	});

	it('returns an empty string when nothing is filtered', () => {
		expect(buildScheduleFiltersQuery({ search: '  ', onlySubscribed: false })).toBe('');
	});
});
