import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// The module keeps its verdict in module state, so each test imports a fresh copy.
async function loadReachability() {
	vi.resetModules();
	return import('./reachability');
}

function healthResponse(status = 200): Response {
	return new Response(null, { status });
}

beforeEach(() => {
	vi.useFakeTimers();
	vi.stubGlobal('navigator', { onLine: true });
});

afterEach(() => {
	vi.useRealTimers();
	vi.unstubAllGlobals();
});

describe('probeReachability', () => {
	// The rule that must not regress silently: on mobile, the first probe after
	// foregrounding often fails while the radio wakes. Alarming on it flashes the
	// offline banner for a connection that is about to work.
	it('stays online when a retry inside the confirm window succeeds', async () => {
		const fetchMock = vi
			.fn<typeof fetch>()
			.mockRejectedValueOnce(new TypeError('Failed to fetch'))
			.mockResolvedValueOnce(healthResponse());
		vi.stubGlobal('fetch', fetchMock);
		const { isReachable, onReachableChange, probeReachability } = await loadReachability();
		const listener = vi.fn();
		onReachableChange(listener);

		const probe = probeReachability();
		await vi.advanceTimersByTimeAsync(1000);

		await expect(probe).resolves.toBe(true);
		expect(isReachable()).toBe(true);
		expect(listener).not.toHaveBeenCalled();
		expect(fetchMock).toHaveBeenCalledTimes(2);
	});

	it('goes offline once the whole confirm window fails', async () => {
		vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockRejectedValue(new TypeError('Failed')));
		const { isReachable, probeReachability } = await loadReachability();

		const probe = probeReachability();
		await vi.advanceTimersByTimeAsync(6000);

		await expect(probe).resolves.toBe(false);
		expect(isReachable()).toBe(false);
	});

	it('trusts a device that reports no network and skips the window', async () => {
		vi.stubGlobal('navigator', { onLine: false });
		const fetchMock = vi.fn<typeof fetch>().mockRejectedValue(new TypeError('Failed'));
		vi.stubGlobal('fetch', fetchMock);
		const { isReachable, probeReachability } = await loadReachability();

		await expect(probeReachability()).resolves.toBe(false);
		expect(isReachable()).toBe(false);
		expect(fetchMock).toHaveBeenCalledTimes(1);
	});

	it('treats a gateway status as the backend being unreachable', async () => {
		vi.stubGlobal('navigator', { onLine: false });
		vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(healthResponse(502)));
		const { isReachable, probeReachability } = await loadReachability();

		await expect(probeReachability()).resolves.toBe(false);
		expect(isReachable()).toBe(false);
	});

	it('counts any other status as reachable, even a 500', async () => {
		vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(healthResponse(500)));
		const { isReachable, markReachable, probeReachability } = await loadReachability();
		markReachable(false);

		await expect(probeReachability()).resolves.toBe(true);
		expect(isReachable()).toBe(true);
	});

	it('drops its verdict when fresher evidence landed while it was in flight', async () => {
		let failPing!: (error: Error) => void;
		const pending = new Promise<Response>((_, reject) => {
			failPing = reject;
		});
		vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockReturnValue(pending));
		const { isReachable, markReachable, probeReachability } = await loadReachability();
		markReachable(false);

		const probe = probeReachability();
		// An API response proves the server reachable before the slow ping fails.
		markReachable(true);
		failPing(new TypeError('Failed'));

		await expect(probe).resolves.toBe(false);
		expect(isReachable()).toBe(true);
	});
});
