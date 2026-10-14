import { describe, expect, it } from 'vitest';

import { buildUserFiltersQuery, parseUserFilters } from './userFilters';

describe('parseUserFilters', () => {
	it('reads every filter from the URL', () => {
		const params = new URLSearchParams('q=%20anna%20&role=helper&ticket=no');
		expect(parseUserFilters(params)).toEqual({
			search: 'anna',
			role: 'helper',
			hasTicket: false
		});
	});

	it('treats missing or unknown values as no filter', () => {
		const params = new URLSearchParams('role=admin&ticket=maybe');
		expect(parseUserFilters(params)).toEqual({ search: '', role: null, hasTicket: null });
	});
});

describe('buildUserFiltersQuery', () => {
	it('round-trips through parseUserFilters', () => {
		const filters = { search: 'FAN-12', role: 'org' as const, hasTicket: true };
		const query = buildUserFiltersQuery(filters);
		expect(parseUserFilters(new URLSearchParams(query))).toEqual(filters);
	});

	it('returns an empty string when nothing is filtered', () => {
		expect(buildUserFiltersQuery({ search: '  ', role: null, hasTicket: null })).toBe('');
	});
});
