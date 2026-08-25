import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// The client middleware calls reportRequestReachability with the first-paint
// timeout budget; mirror it here so the window matches production.
const WINDOW_MS = 3500;

// Reachability state is module-global, so reset the module between cases to start
// each from the optimistic default (reachable = true).
async function freshModule() {
	vi.resetModules();
	return import('./reachability');
}

describe('reportRequestReachability', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		vi.setSystemTime(0);
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('marks unreachable on a failure with no prior success', async () => {
		const { reportRequestReachability, isReachable } = await freshModule();

		reportRequestReachability(false, WINDOW_MS);

		expect(isReachable()).toBe(false);
	});

	it('marks reachable on a successful request', async () => {
		const { reportRequestReachability, isReachable } = await freshModule();

		reportRequestReachability(false, WINDOW_MS);
		reportRequestReachability(true, WINDOW_MS);

		expect(isReachable()).toBe(true);
	});

	it('suppresses a failure that lands within the window after a success', async () => {
		const { reportRequestReachability, isReachable } = await freshModule();

		// The notification preview succeeds…
		reportRequestReachability(true, WINDOW_MS);
		// …then its unread-count sibling times out just under the budget later.
		vi.setSystemTime(WINDOW_MS - 1);
		reportRequestReachability(false, WINDOW_MS);

		expect(isReachable()).toBe(true);
	});

	it('marks unreachable once a failure lands after the window', async () => {
		const { reportRequestReachability, isReachable } = await freshModule();

		reportRequestReachability(true, WINDOW_MS);
		vi.setSystemTime(WINDOW_MS);
		reportRequestReachability(false, WINDOW_MS);

		expect(isReachable()).toBe(false);
	});
});
