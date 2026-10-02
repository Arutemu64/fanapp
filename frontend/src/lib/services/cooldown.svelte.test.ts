import type * as Svelte from 'svelte';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// useInterval registers onDestroy, which throws outside component initialization.
vi.mock('svelte', async (importOriginal) => ({
	...(await importOriginal<typeof Svelte>()),
	onDestroy: () => {}
}));

import { ResendCooldown } from './cooldown.svelte';

beforeEach(() => {
	vi.useFakeTimers();
});

afterEach(() => {
	vi.useRealTimers();
});

describe('ResendCooldown', () => {
	it('starts ready', () => {
		expect(new ResendCooldown(3).remaining).toBe(0);
	});

	it('counts down once per second after start()', () => {
		const cooldown = new ResendCooldown(3);
		cooldown.start();
		expect(cooldown.remaining).toBe(3);
		vi.advanceTimersByTime(1000);
		expect(cooldown.remaining).toBe(2);
		vi.advanceTimersByTime(2000);
		expect(cooldown.remaining).toBe(0);
	});

	it('stops ticking once it reaches zero', () => {
		const cooldown = new ResendCooldown(1);
		cooldown.start();
		vi.advanceTimersByTime(2000);
		expect(cooldown.remaining).toBe(0);
		expect(vi.getTimerCount()).toBe(0);
	});

	it('stop() freezes the remaining time', () => {
		const cooldown = new ResendCooldown(5);
		cooldown.start();
		vi.advanceTimersByTime(2000);
		cooldown.stop();
		vi.advanceTimersByTime(5000);
		expect(cooldown.remaining).toBe(3);
	});

	it('reset() clears the countdown', () => {
		const cooldown = new ResendCooldown(5);
		cooldown.start();
		cooldown.reset();
		expect(cooldown.remaining).toBe(0);
		expect(vi.getTimerCount()).toBe(0);
	});

	it('start() again restarts from the full duration', () => {
		const cooldown = new ResendCooldown(5);
		cooldown.start();
		vi.advanceTimersByTime(3000);
		cooldown.start();
		expect(cooldown.remaining).toBe(5);
	});
});
