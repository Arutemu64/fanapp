import { describe, expect, it } from 'vitest';

import { keyboardInset } from './keyboardInset';

describe('keyboardInset', () => {
	it('is zero with no keyboard', () => {
		expect(keyboardInset(800, { height: 800, offsetTop: 0, scale: 1 })).toBe(0);
	});

	it('is the strip the keyboard covers', () => {
		expect(keyboardInset(800, { height: 460, offsetTop: 0, scale: 1 })).toBe(340);
	});

	it('subtracts the pan iOS adds to bring a focused field into view', () => {
		expect(keyboardInset(800, { height: 460, offsetTop: 120, scale: 1 })).toBe(220);
	});

	it('ignores a pinch-zoom, which shrinks the visual viewport too', () => {
		expect(keyboardInset(800, { height: 400, offsetTop: 100, scale: 2 })).toBe(0);
	});

	it('never goes negative', () => {
		expect(keyboardInset(800, { height: 820, offsetTop: 0, scale: 1 })).toBe(0);
	});
});
