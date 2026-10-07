export type ReadyStepKey = 'account' | 'install' | 'notifications' | 'subscribe' | 'ticket';

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
	canInstall: boolean;
	/**
	 * iOS only delivers web push to a Home Screen app
	 * (https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/), so
	 * there installing has to come before notifications can be switched on.
	 */
	installBeforeNotifications: boolean;
}

/**
 * The setup steps still open for this viewer, most important first. Each step
 * drops out once its condition holds, so the list differs per person and runs
 * empty once everything is done — the home page then hides the section.
 */
export function getReadySteps(input: ReadyStepsInput): ReadyStepKey[] {
	if (!input.signedIn) {
		return input.canInstall ? ['account', 'install'] : ['account'];
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
		if (input.canInstall) steps.push('install');
		if (needsNotifications) steps.push('notifications');
	} else {
		if (needsNotifications) steps.push('notifications');
		if (input.canInstall) steps.push('install');
	}

	return steps;
}
