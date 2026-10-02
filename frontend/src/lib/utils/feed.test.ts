import { describe, expect, it } from 'vitest';

import { dedupeById, feedSnapshotKey } from './feed';

describe('feedSnapshotKey', () => {
	it('encodes the flag and the ids in order', () => {
		expect(feedSnapshotKey(true, [1, 'b', 3])).toBe('true:1:b:3');
	});

	it('differs when only the flag differs', () => {
		expect(feedSnapshotKey(true, [1])).not.toBe(feedSnapshotKey(false, [1]));
	});
});

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
