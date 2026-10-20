import { describe, expect, it } from 'vitest';

import { createMapSearch } from './mapSearch';

const maps = [
	{
		id: 'floor-1',
		label: () => '1 этаж',
		points: [
			{ number: 8, name: () => 'Кофейня', keywords: ['кофе', 'еда'] },
			{ number: 9, name: () => 'Женский туалет', keywords: ['wc'] }
		]
	},
	{
		id: 'floor-2-3',
		label: () => '2 и 3 этажи',
		points: [
			{ number: 13, name: () => 'Мужской туалет', keywords: ['wc'] },
			{ number: 15, name: () => 'Just Dance', floor: () => '3 этаж' }
		]
	}
];

const search = createMapSearch(maps);

describe('createMapSearch', () => {
	it('finds a place on every floor, in plan order', () => {
		expect(search('туалет').map((result) => [result.mapId, result.point.number])).toEqual([
			['floor-1', 9],
			['floor-2-3', 13]
		]);
	});

	it('matches an alias the name lacks', () => {
		expect(search('WC')).toHaveLength(2);
		expect(search('кофе').map((result) => result.point.number)).toEqual([8]);
	});

	it("labels a point with its own floor before its plan's", () => {
		expect(search('just dance')[0]?.floorLabel).toBe('3 этаж');
		expect(search('кофейня')[0]?.floorLabel).toBe('1 этаж');
	});

	it('finds nothing for an unknown word', () => {
		expect(search('бассейн')).toEqual([]);
	});
});
