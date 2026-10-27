import { describe, expect, it } from 'vitest';

import { qrPath } from './qrPath';

describe('qrPath', () => {
	it('draws a version 1 code inside a four-module quiet zone', () => {
		const { size, d } = qrPath('fanfan');

		expect(size).toBe(29);
		expect(d.startsWith('M4 4h1v1h-1z')).toBe(true);
	});

	it('leaves the quiet zone empty', () => {
		const { size, d } = qrPath('fanfan');
		const coordinates = [...d.matchAll(/M(\d+) (\d+)/g)].map(([, x, y]) => [Number(x), Number(y)]);

		for (const [x, y] of coordinates) {
			expect(x).toBeGreaterThanOrEqual(4);
			expect(y).toBeGreaterThanOrEqual(4);
			expect(x).toBeLessThan(size - 4);
			expect(y).toBeLessThan(size - 4);
		}
	});
});
