import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { withTimeout } from './fetchTimeout.js';

describe('withTimeout', () => {
	beforeEach(() => vi.useFakeTimers());
	afterEach(() => vi.useRealTimers());

	it('resolves with the promise when it settles in time', async () => {
		await expect(withTimeout(Promise.resolve('ok'), 1000)).resolves.toBe('ok');
		expect(vi.getTimerCount()).toBe(0);
	});

	it('passes the promise rejection through', async () => {
		await expect(withTimeout(Promise.reject(new Error('boom')), 1000)).rejects.toThrow('boom');
		expect(vi.getTimerCount()).toBe(0);
	});

	it('rejects with a TimeoutError when the promise stays pending', async () => {
		const result = withTimeout(new Promise<never>(() => {}), 1000);
		const assertion = expect(result).rejects.toMatchObject({ name: 'TimeoutError' });
		await vi.advanceTimersByTimeAsync(1000);
		await assertion;
	});
});
