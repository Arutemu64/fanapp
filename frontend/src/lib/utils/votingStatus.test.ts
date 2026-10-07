import { describe, expect, it } from 'vitest';

import { hasVotingEnded, isVotingWindowOpen } from './votingStatus';

const START = '2026-10-10T10:00:00Z';
const END = '2026-10-10T18:00:00Z';
const startMs = new Date(START).getTime();
const endMs = new Date(END).getTime();

describe('isVotingWindowOpen', () => {
	it('is open on [start, end), like the backend', () => {
		expect(isVotingWindowOpen(START, END, startMs - 1)).toBe(false);
		expect(isVotingWindowOpen(START, END, startMs)).toBe(true);
		expect(isVotingWindowOpen(START, END, endMs - 1)).toBe(true);
		expect(isVotingWindowOpen(START, END, endMs)).toBe(false);
	});

	it('is closed when either bound is missing', () => {
		expect(isVotingWindowOpen(null, END, startMs)).toBe(false);
		expect(isVotingWindowOpen(START, undefined, startMs)).toBe(false);
	});
});

describe('hasVotingEnded', () => {
	it('is true from the end instant on', () => {
		expect(hasVotingEnded(END, endMs - 1)).toBe(false);
		expect(hasVotingEnded(END, endMs)).toBe(true);
	});

	it('is false while no end is configured', () => {
		expect(hasVotingEnded(null, endMs)).toBe(false);
	});
});
