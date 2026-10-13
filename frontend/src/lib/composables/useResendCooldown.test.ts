import { effectScope } from 'vue';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useResendCooldown } from './useResendCooldown';

beforeEach(() => {
	vi.useFakeTimers();
});

afterEach(() => {
	vi.useRealTimers();
});

describe('useResendCooldown', () => {
	it('starts ready', () => {
		expect(useResendCooldown(3).remaining.value).toBe(0);
	});

	it('counts down once per second after start()', () => {
		const cooldown = useResendCooldown(3);
		cooldown.start();
		expect(cooldown.remaining.value).toBe(3);
		vi.advanceTimersByTime(1000);
		expect(cooldown.remaining.value).toBe(2);
		vi.advanceTimersByTime(2000);
		expect(cooldown.remaining.value).toBe(0);
	});

	it('stops ticking once it reaches zero', () => {
		const cooldown = useResendCooldown(1);
		cooldown.start();
		vi.advanceTimersByTime(2000);
		expect(cooldown.remaining.value).toBe(0);
		expect(vi.getTimerCount()).toBe(0);
	});

	it('stop() freezes the remaining time', () => {
		const cooldown = useResendCooldown(5);
		cooldown.start();
		vi.advanceTimersByTime(2000);
		cooldown.stop();
		vi.advanceTimersByTime(5000);
		expect(cooldown.remaining.value).toBe(3);
	});

	it('reset() clears the countdown', () => {
		const cooldown = useResendCooldown(5);
		cooldown.start();
		cooldown.reset();
		expect(cooldown.remaining.value).toBe(0);
		expect(vi.getTimerCount()).toBe(0);
	});

	it('start() again restarts from the full duration', () => {
		const cooldown = useResendCooldown(5);
		cooldown.start();
		vi.advanceTimersByTime(3000);
		cooldown.start();
		expect(cooldown.remaining.value).toBe(5);
	});

	it('stops ticking when the owning scope is disposed', () => {
		const scope = effectScope();
		const cooldown = scope.run(() => useResendCooldown(5))!;
		cooldown.start();
		scope.stop();
		expect(vi.getTimerCount()).toBe(0);
		vi.advanceTimersByTime(5000);
		expect(cooldown.remaining.value).toBe(5);
	});
});
