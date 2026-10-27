import type { CurrentUserDto } from '#lib/api/generated/index.js';
import type { DevicePushState } from '#lib/services/pushDevice.svelte.js';

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

	const needsNotifications = input.notificationsOn === false;
	if (input.installBeforeNotifications) {
		if (canInstall) steps.push('install');
		if (needsNotifications) steps.push('notifications');
	} else {
		if (needsNotifications) steps.push('notifications');
		if (canInstall) steps.push('install');
	}

	return steps;
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

function hasMessengerNotifications(user: CurrentUserDto): boolean {
	const providers = user.social_identities.map((identity) => identity.provider);
	const telegramOn = providers.includes('telegram') && user.settings.receive_telegram_notifications;
	const vkOn = providers.includes('vk') && user.settings.receive_vk_notifications;
	return telegramOn || vkOn;
}
