import { describe, expect, it } from 'vitest';

import { getReadySteps, type ReadyStepsInput } from './readySteps';

// A signed-in viewer with every step done: each test opens exactly the steps it checks.
const DONE: ReadyStepsInput = {
	signedIn: true,
	hasTicket: true,
	votingEnded: false,
	ticketAskedElsewhere: false,
	hasProgramme: true,
	hasSubscriptions: true,
	notificationsOn: true,
	canInstall: false,
	installBeforeNotifications: false
};

describe('getReadySteps', () => {
	it('asks a guest only to sign in, plus install where it is offered', () => {
		expect(getReadySteps({ ...DONE, signedIn: false, hasTicket: false })).toEqual(['account']);
		expect(getReadySteps({ ...DONE, signedIn: false, canInstall: true })).toEqual([
			'account',
			'install'
		]);
	});

	it('runs empty once everything is done', () => {
		expect(getReadySteps(DONE)).toEqual([]);
	});

	it('lists open steps for a new account in priority order', () => {
		const steps = getReadySteps({
			...DONE,
			hasTicket: false,
			hasSubscriptions: false,
			notificationsOn: false,
			canInstall: true
		});

		expect(steps).toEqual(['ticket', 'subscribe', 'notifications', 'install']);
	});

	it('puts install before notifications where push needs an installed app', () => {
		const steps = getReadySteps({
			...DONE,
			notificationsOn: false,
			canInstall: true,
			installBeforeNotifications: true
		});

		expect(steps).toEqual(['install', 'notifications']);
	});

	it('drops the ticket step once voting has ended or the voting card asks for it', () => {
		expect(getReadySteps({ ...DONE, hasTicket: false, votingEnded: true })).toEqual([]);
		expect(getReadySteps({ ...DONE, hasTicket: false, ticketAskedElsewhere: true })).toEqual([]);
	});

	it('skips subscribing until a programme is published', () => {
		expect(getReadySteps({ ...DONE, hasProgramme: false, hasSubscriptions: false })).toEqual([]);
	});

	it('hides the notifications step while the device check is pending', () => {
		expect(getReadySteps({ ...DONE, notificationsOn: null })).toEqual([]);
	});
});
