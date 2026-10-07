import { describe, expect, it } from 'vitest';

import { getReadyProgress, type ReadyStepsInput } from './readySteps';

// A signed-in viewer with every step done: each test opens exactly the steps it checks.
const DONE: ReadyStepsInput = {
	signedIn: true,
	hasTicket: true,
	votingEnded: false,
	ticketAskedElsewhere: false,
	hasProgramme: true,
	hasSubscriptions: true,
	notificationsOn: true,
	install: 'installed',
	installBeforeNotifications: false
};

describe('getReadyProgress', () => {
	it('offers a guest only sign-in, plus install where it applies', () => {
		const guest = { ...DONE, signedIn: false, hasTicket: false };

		expect(getReadyProgress({ ...guest, install: 'unavailable' })).toEqual({
			open: ['account'],
			done: 0,
			total: 1
		});
		expect(getReadyProgress({ ...guest, install: 'available' })).toEqual({
			open: ['account', 'install'],
			done: 0,
			total: 2
		});
	});

	it('has nothing open once everything is done, and counts the account', () => {
		expect(getReadyProgress(DONE)).toEqual({ open: [], done: 5, total: 5 });
	});

	it('lists open steps for a new account in priority order', () => {
		const progress = getReadyProgress({
			...DONE,
			hasTicket: false,
			hasSubscriptions: false,
			notificationsOn: false,
			install: 'available'
		});

		expect(progress).toEqual({
			open: ['ticket', 'subscribe', 'notifications', 'install'],
			done: 1,
			total: 5
		});
	});

	it('puts install before notifications where push needs an installed app', () => {
		const progress = getReadyProgress({
			...DONE,
			notificationsOn: false,
			install: 'available',
			installBeforeNotifications: true
		});

		expect(progress.open).toEqual(['install', 'notifications']);
	});

	it('drops the ticket step once voting has ended or the voting card asks for it', () => {
		const ended = getReadyProgress({ ...DONE, hasTicket: false, votingEnded: true });
		const askedElsewhere = getReadyProgress({
			...DONE,
			hasTicket: false,
			ticketAskedElsewhere: true
		});

		expect(ended).toEqual({ open: [], done: 4, total: 4 });
		expect(askedElsewhere).toEqual({ open: [], done: 4, total: 4 });
	});

	it('skips subscribing until a programme is published', () => {
		const progress = getReadyProgress({ ...DONE, hasProgramme: false, hasSubscriptions: false });

		expect(progress).toEqual({ open: [], done: 4, total: 4 });
	});

	it('leaves notifications out while the device check is pending', () => {
		expect(getReadyProgress({ ...DONE, notificationsOn: null })).toEqual({
			open: [],
			done: 4,
			total: 4
		});
	});

	it('leaves install out where the browser cannot install', () => {
		expect(getReadyProgress({ ...DONE, install: 'unavailable' }).total).toBe(4);
	});
});
