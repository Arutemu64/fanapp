import { describe, expect, it } from 'vitest';

import { dedupeById } from './feed';

describe('dedupeById', () => {
	it('drops items from `next` whose id is already present', () => {
		expect(dedupeById([{ id: 1 }, { id: 2 }], [{ id: 2 }, { id: 3 }])).toEqual([
			{ id: 1 },
			{ id: 2 },
			{ id: 3 }
		]);
	});

	it('keeps the existing copy and the order', () => {
		const result = dedupeById(
			[{ id: 2, v: 'old' }],
			[
				{ id: 1, v: 'x' },
				{ id: 2, v: 'new' }
			]
		);
		expect(result).toEqual([
			{ id: 2, v: 'old' },
			{ id: 1, v: 'x' }
		]);
	});

	it('handles empty input', () => {
		expect(dedupeById([], [])).toEqual([]);
		expect(dedupeById([{ id: 1 }], [])).toEqual([{ id: 1 }]);
		expect(dedupeById([], [{ id: 1 }])).toEqual([{ id: 1 }]);
	});
});
