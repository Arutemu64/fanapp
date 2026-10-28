import type { CurrentUserDto } from '#lib/api/generated/index.js';
import type { DevicePushState } from '#lib/services/pushDevice.svelte.js';

import { hasMessengerNotifications } from '#lib/utils/users.js';

export type ReadyStepKey = 'account' | 'install' | 'notifications' | 'subscribe' | 'ticket';

export type InstallState = 'available' | 'installed' | 'unavailable';

export interface ReadyStepsInput {
	signedIn: boolean;
	hasTicket: boolean;
	votingEnded: boolean;
	ticketAskedElsewhere: boolean;
	hasProgramme: boolean;
	hasSubscriptions: boolean;
	notificationsOn: boolean | null;
	install: InstallState;
	installBeforeNotifications: boolean;
}

export function getReadySteps(input: ReadyStepsInput): ReadyStepKey[] {
	const canInstall = input.install === 'available';

	if (!input.signedIn) {
		return canInstall ? ['account', 'install'] : ['account'];
	}

	const steps: ReadyStepKey[] = [];

	if (!input.hasTicket && !input.votingEnded && !input.ticketAskedElsewhere) {
		steps.push('ticket');
	}
	if (input.hasProgramme && !input.hasSubscriptions) {
		steps.push('subscribe');
	}

	steps.push(...getDeviceSteps(input));
	return steps;
}

function getDeviceSteps(input: ReadyStepsInput): ReadyStepKey[] {
	const install: ReadyStepKey[] = input.install === 'available' ? ['install'] : [];
	const notifications: ReadyStepKey[] = input.notificationsOn === false ? ['notifications'] : [];
	if (input.installBeforeNotifications) return [...install, ...notifications];
	return [...notifications, ...install];
}

export function getNotificationsOn(
	user: CurrentUserDto | null,
	devicePush: DevicePushState
): boolean | null {
	if (user && hasMessengerNotifications(user)) return true;
	if (devicePush === 'on') return true;
	if (devicePush === 'off') return false;
	return null;
}
