import type { GetVotingStateOutput } from '$lib/api/generated';

import { describe, expect, it } from 'vitest';

import { hasVotingEnded, isVotingOpenNow, isVotingWindowOpen } from './votingStatus';

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

describe('isVotingOpenNow', () => {
	function state(status: GetVotingStateOutput['status']): GetVotingStateOutput {
		return { can_vote: status === 'open', status, voting_start: START, voting_end: END };
	}

	it('trusts the server over a client clock that runs ahead', () => {
		expect(isVotingOpenNow(state('disabled'), startMs)).toBe(false);
	});

	it('uses the window for statuses that say nothing about it', () => {
		expect(isVotingOpenNow(state('no_ticket'), startMs)).toBe(true);
		expect(isVotingOpenNow(state('not_authenticated'), endMs)).toBe(false);
	});

	it('closes an open status once the window ends on the client', () => {
		expect(isVotingOpenNow(state('open'), endMs)).toBe(false);
	});

	it('is closed without a status', () => {
		expect(isVotingOpenNow(undefined, startMs)).toBe(false);
	});
});
