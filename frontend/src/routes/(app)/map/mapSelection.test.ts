import { describe, expect, it } from 'vitest';

import { buildMapSelectionQuery, parseMapSelection } from './mapSelection';

describe('parseMapSelection', () => {
	it('reads the floor and the place from the URL', () => {
		const params = new URLSearchParams('floor=floor-2-3&place=14');
		expect(parseMapSelection(params)).toEqual({ floorId: 'floor-2-3', placeNumber: 14 });
	});

	it('opens the first floor with nothing picked for a bare /map', () => {
		expect(parseMapSelection(new URLSearchParams())).toEqual({
			floorId: 'floor-1',
			placeNumber: null
		});
	});

	it('drops an unknown floor and a place that is not on the floor', () => {
		const params = new URLSearchParams('floor=roof&place=999');
		expect(parseMapSelection(params)).toEqual({ floorId: 'floor-1', placeNumber: null });
	});
});

describe('buildMapSelectionQuery', () => {
	it('round-trips through parseMapSelection', () => {
		const selection = { floorId: 'floor-2-3', placeNumber: 7 };
		const query = buildMapSelectionQuery(selection);
		expect(parseMapSelection(new URLSearchParams(query))).toEqual(selection);
	});

	it('leaves the first floor with nothing picked as a bare /map', () => {
		expect(buildMapSelectionQuery({ floorId: 'floor-1', placeNumber: null })).toBe('');
	});
});
