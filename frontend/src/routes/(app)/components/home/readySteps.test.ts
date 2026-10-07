import type { CurrentUserDto } from '$lib/api/generated';

import { describe, expect, it } from 'vitest';

import { getNotificationsOn, getReadySteps, type ReadyStepsInput } from './readySteps';

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

describe('getReadySteps', () => {
	it('offers a guest only sign-in, plus install where it is available', () => {
		const guest = { ...DONE, signedIn: false, hasTicket: false };

		expect(getReadySteps({ ...guest, install: 'unavailable' })).toEqual(['account']);
		expect(getReadySteps({ ...guest, install: 'available' })).toEqual(['account', 'install']);
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
			install: 'available'
		});

		expect(steps).toEqual(['ticket', 'subscribe', 'notifications', 'install']);
	});

	it('puts install before notifications where push needs an installed app', () => {
		const steps = getReadySteps({
			...DONE,
			notificationsOn: false,
			install: 'available',
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

	it('hides install where the browser cannot install', () => {
		expect(getReadySteps({ ...DONE, install: 'unavailable' })).toEqual([]);
	});
});

function member(overrides: Partial<CurrentUserDto> = {}): CurrentUserDto {
	return {
		id: 'u',
		username: 'visitor',
		role: 'visitor',
		email: null,
		has_password: true,
		ticket: null,
		permissions: [],
		settings: {
			receive_all_announcements: true,
			receive_telegram_notifications: true,
			receive_vk_notifications: true
		},
		social_identities: [],
		...overrides
	};
}

describe('getNotificationsOn', () => {
	it('follows the device push state when no messenger is linked', () => {
		expect(getNotificationsOn(member(), 'on')).toBe(true);
		expect(getNotificationsOn(member(), 'off')).toBe(false);
		expect(getNotificationsOn(member(), 'unknown')).toBeNull();
	});

	it('counts a linked messenger with notifications on, whatever the device says', () => {
		const telegram = member({
			social_identities: [{ provider: 'telegram' }]
		});

		expect(getNotificationsOn(telegram, 'off')).toBe(true);
	});

	it('ignores a linked messenger whose notifications are off', () => {
		const vkMuted = member({
			social_identities: [{ provider: 'vk' }],
			settings: {
				receive_all_announcements: true,
				receive_telegram_notifications: true,
				receive_vk_notifications: false
			}
		});

		expect(getNotificationsOn(vkMuted, 'off')).toBe(false);
	});
});
