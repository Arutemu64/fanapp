import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const fake = vi.hoisted(() => {
	let reachable = true;
	const listeners = new Set<() => void>();
	return {
		set: (value: boolean) => {
			if (value === reachable) return;
			reachable = value;
			for (const listener of listeners) listener();
		},
		reset: () => {
			reachable = true;
			listeners.clear();
		},
		isReachable: () => reachable,
		onReachableChange: (listener: () => void) => {
			listeners.add(listener);
			return () => void listeners.delete(listener);
		}
	};
});
vi.mock('./reachability', () => ({
	isReachable: fake.isReachable,
	markReachable: fake.set,
	onReachableChange: fake.onReachableChange,
	probeReachability: vi.fn(() => Promise.resolve(fake.isReachable()))
}));

const { startReachabilityMonitor } = await import('./reachabilityMonitor.js');

beforeEach(() => {
	vi.useFakeTimers();
	fake.reset();
	vi.stubGlobal('window', new EventTarget());
	vi.stubGlobal('document', Object.assign(new EventTarget(), { visibilityState: 'visible' }));
});

afterEach(() => {
	vi.useRealTimers();
	vi.unstubAllGlobals();
});

describe('startReachabilityMonitor', () => {
	it('reports the offline→online edge, so the root layout can flush a queued logout', () => {
		const onRecovered = vi.fn();
		const stop = startReachabilityMonitor({ onRecovered });

		fake.set(false);
		expect(onRecovered).not.toHaveBeenCalled();
		fake.set(true);

		expect(onRecovered).toHaveBeenCalledOnce();
		stop();
	});

	it('stays quiet once torn down, so an HMR restart cannot double-flush', () => {
		const onRecovered = vi.fn();
		const stop = startReachabilityMonitor({ onRecovered });
		stop();

		fake.set(false);
		fake.set(true);

		expect(onRecovered).not.toHaveBeenCalled();
	});
});
