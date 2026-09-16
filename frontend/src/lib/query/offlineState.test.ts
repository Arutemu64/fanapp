import { describe, expect, it } from 'vitest';

import { offlineQueryState } from './offlineState';

// A query that has succeeded at some point, with the knobs each test flips.
function query(overrides: Partial<Parameters<typeof offlineQueryState>[0]> = {}) {
	return {
		data: ['event'],
		dataUpdatedAt: 1_700_000_000_000,
		isError: false,
		isPaused: false,
		...overrides
	};
}

describe('offlineQueryState', () => {
	it('reports fresh data as neither stale nor a miss', () => {
		expect(offlineQueryState(query(), true)).toEqual({
			cachedAt: 1_700_000_000_000,
			offlineMiss: false,
			stale: false
		});
	});

	it('marks a paused query stale — the restored copy is what is on screen', () => {
		const state = offlineQueryState(query({ isPaused: true }), false);

		expect(state.stale).toBe(true);
		expect(state.offlineMiss).toBe(false);
		expect(state.cachedAt).toBe(1_700_000_000_000);
	});

	it('marks a failed-but-populated query stale rather than a miss', () => {
		expect(offlineQueryState(query({ isError: true }), true).stale).toBe(true);
	});

	it('reports a cold offline start as an offline miss', () => {
		expect(offlineQueryState(query({ data: undefined, dataUpdatedAt: 0 }), false)).toEqual({
			cachedAt: undefined,
			offlineMiss: true,
			stale: true
		});
	});

	it('does not call an online first load a miss — it is still loading', () => {
		const state = offlineQueryState(query({ data: undefined, dataUpdatedAt: 0 }), true);

		expect(state.offlineMiss).toBe(false);
		expect(state.stale).toBe(false);
	});

	it('drops the never-fetched timestamp instead of rendering it as 1970', () => {
		expect(offlineQueryState(query({ dataUpdatedAt: 0 }), true).cachedAt).toBeUndefined();
	});
});
