import type { CurrentUserDto } from '$lib/api/generated';
import type { DevicePushState } from '$lib/utils/pushSubscription';

export type ReadyStepKey = 'account' | 'install' | 'notifications' | 'subscribe' | 'ticket';

export type InstallState = 'available' | 'installed' | 'unavailable';

export interface ReadyStepsInput {
	signedIn: boolean;
	hasTicket: boolean;
	/** Once voting has closed a ticket unlocks nothing, so the step expires with it. */
	votingEnded: boolean;
	/** The voting card is already asking for the ticket — don't ask twice. */
	ticketAskedElsewhere: boolean;
	hasProgramme: boolean;
	hasSubscriptions: boolean;
	/** Null while unknown (the device check hasn't answered): the step stays hidden. */
	notificationsOn: boolean | null;
	install: InstallState;
	/**
	 * iOS and iPadOS deliver web push only to a Home Screen app
	 * (https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/), so
	 * there installing has to come before notifications can be switched on. Not on
	 * a Mac: Safari there delivers push to an ordinary tab.
	 */
	installBeforeNotifications: boolean;
}

/**
 * The setup steps still open for this viewer, most important first. Each step
 * drops out once its condition holds, so the list differs per person and runs
 * empty once everything is done — the home page then hides the section. There
 * is deliberately no done/total count: which steps apply varies by device and
 * moment (install support, the async push check, the voting window), so a total
 * would shift under the viewer.
 */
export function getReadySteps(input: ReadyStepsInput): ReadyStepKey[] {
	const canInstall = input.install === 'available';

	// Every other step needs an account, so a guest is offered only what they can
	// do right now.
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

/**
 * Whether reminders reach this viewer, or null while the device check is still
 * pending. A messenger channel counts as much as push on this device: either
 * way the reminders arrive.
 */
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
	const telegramOn =
		providers.includes('telegram') && (user.settings.receive_telegram_notifications ?? false);
	const vkOn = providers.includes('vk') && (user.settings.receive_vk_notifications ?? false);
	return telegramOn || vkOn;
}
