import { describe, expect, it } from 'vitest';

import { classifyReachabilityChange } from './reachabilityTransition';

describe('classifyReachabilityChange', () => {
	it('confirms instead of alarming when a probe fails but the device is still online', () => {
		// The resume-from-background flash: the first probe fails while the radio
		// wakes, yet the device reports online — verify before showing offline.
		expect(
			classifyReachabilityChange({ wasOnline: true, probeReachable: false, deviceOnline: true })
		).toBe('confirm');
	});

	it('goes offline immediately when the device itself reports no network', () => {
		// navigator.onLine === false is a trustworthy negative; no point probing.
		expect(
			classifyReachabilityChange({ wasOnline: true, probeReachable: false, deviceOnline: false })
		).toBe('go-offline');
	});

	it('recovers immediately on the offline→online edge', () => {
		expect(
			classifyReachabilityChange({ wasOnline: false, probeReachable: true, deviceOnline: true })
		).toBe('go-online');
	});

	it('is a noop while already offline and still unreachable', () => {
		// Repeated failed probes during an outage must not restart the confirm window.
		expect(
			classifyReachabilityChange({ wasOnline: false, probeReachable: false, deviceOnline: true })
		).toBe('noop');
		expect(
			classifyReachabilityChange({ wasOnline: false, probeReachable: false, deviceOnline: false })
		).toBe('noop');
	});

	it('is a noop while already online and still reachable', () => {
		expect(
			classifyReachabilityChange({ wasOnline: true, probeReachable: true, deviceOnline: true })
		).toBe('noop');
	});
});
