import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const refreshAll = vi.hoisted(() => vi.fn<() => Promise<void>>());
vi.mock('$app/navigation', () => ({ refreshAll }));

// The debounce clock is module state, so each test imports a fresh copy.
async function loadModule() {
	vi.resetModules();
	return import('./reconnectRefresh');
}

beforeEach(() => {
	vi.useFakeTimers();
	refreshAll.mockReset().mockResolvedValue();
});

afterEach(() => {
	vi.useRealTimers();
});

describe('requestReconnectRefresh', () => {
	it('re-runs the loads and notifies catch-up subscribers', async () => {
		const { onCatchUp, requestReconnectRefresh } = await loadModule();
		const listener = vi.fn();
		onCatchUp(listener);

		requestReconnectRefresh();

		expect(refreshAll).toHaveBeenCalledTimes(1);
		expect(listener).toHaveBeenCalledTimes(1);
	});

	// One recovery trips several paths at once (online edge, SSE handshake); they
	// must collapse into one leading refresh plus at most one trailing one.
	it('collapses a burst into a leading and a single trailing refresh', async () => {
		const { onCatchUp, requestReconnectRefresh } = await loadModule();
		const listener = vi.fn();
		onCatchUp(listener);

		requestReconnectRefresh();
		requestReconnectRefresh();
		requestReconnectRefresh();
		expect(listener).toHaveBeenCalledTimes(1);

		await vi.advanceTimersByTimeAsync(3000);
		expect(listener).toHaveBeenCalledTimes(2);
		expect(refreshAll).toHaveBeenCalledTimes(2);
	});

	it('stops notifying a subscriber once it unsubscribes', async () => {
		const { onCatchUp, requestReconnectRefresh } = await loadModule();
		const listener = vi.fn();
		const unsubscribe = onCatchUp(listener);
		unsubscribe();

		requestReconnectRefresh();

		expect(listener).not.toHaveBeenCalled();
	});
});
