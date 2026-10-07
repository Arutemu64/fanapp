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
	/** Null while unknown (the device check hasn't answered): the step is left out. */
	notificationsOn: boolean | null;
	install: InstallState;
	/**
	 * iOS only delivers web push to a Home Screen app
	 * (https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/), so
	 * there installing has to come before notifications can be switched on.
	 */
	installBeforeNotifications: boolean;
}

export interface ReadyProgress {
	/** Steps still to do, most important first. */
	open: ReadyStepKey[];
	done: number;
	total: number;
}

interface Step {
	key: ReadyStepKey;
	done: boolean;
}

/**
 * The setup steps that apply to this viewer and which of them are done. Done
 * steps drop out of `open` but still count toward `done`/`total`, so the list
 * stays short while the counter shows how far along the viewer is. Which steps
 * apply depends on the viewer, so the list differs per person.
 */
export function getReadyProgress(input: ReadyStepsInput): ReadyProgress {
	const steps = input.signedIn ? memberSteps(input) : guestSteps(input);

	const open = steps.filter((step) => !step.done).map((step) => step.key);
	const done = steps.length - open.length;

	return { open, done, total: steps.length };
}

// Every other step needs an account, so a guest is offered only what they can
// do right now.
function guestSteps(input: ReadyStepsInput): Step[] {
	const steps: Step[] = [{ key: 'account', done: false }];
	if (input.install !== 'unavailable') {
		steps.push({ key: 'install', done: input.install === 'installed' });
	}
	return steps;
}

function memberSteps(input: ReadyStepsInput): Step[] {
	const steps: Step[] = [{ key: 'account', done: true }];

	if (!input.votingEnded && !input.ticketAskedElsewhere) {
		steps.push({ key: 'ticket', done: input.hasTicket });
	}
	if (input.hasProgramme) {
		steps.push({ key: 'subscribe', done: input.hasSubscriptions });
	}

	const notifications: Step[] = [];
	if (input.notificationsOn !== null) {
		notifications.push({ key: 'notifications', done: input.notificationsOn });
	}
	const install: Step[] = [];
	if (input.install !== 'unavailable') {
		install.push({ key: 'install', done: input.install === 'installed' });
	}

	if (input.installBeforeNotifications) {
		steps.push(...install, ...notifications);
	} else {
		steps.push(...notifications, ...install);
	}

	return steps;
}
