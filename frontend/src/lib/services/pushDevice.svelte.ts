import * as Sentry from '@sentry/sveltekit';

import { getApiErrorCode } from '#lib/api/errors.js';

import { browserPush, type PushBrowser } from './pushBrowser.js';

export type PushDeviceState = 'on' | 'off' | 'unknown' | 'blocked' | 'unsupported';

export type DevicePushState = 'on' | 'off' | 'unknown';

export type PushToggleOutcome =
	| 'enabled'
	| 'disabled'
	| 'unsupported'
	| 'unavailable'
	| 'blocked'
	| 'not-granted'
	| 'incomplete'
	| 'rejected'
	| 'failed'
	| 'disable-failed';

interface PushRegistration {
	endpoint: string;
	p256dh: string;
	auth: string;
}

export interface PushBackend {
	isRegistered: (endpoint: string) => Promise<boolean>;
	register: (registration: PushRegistration) => Promise<void>;
	unregister: (endpoint: string) => Promise<void>;
}

async function inspectBrowser(
	browser: PushBrowser
): Promise<PushSubscription | 'unsupported' | 'blocked' | 'off'> {
	if (!browser.isSupported()) {
		return 'unsupported';
	}
	if (browser.permission() === 'denied') {
		return 'blocked';
	}
	return (await browser.getSubscription()) ?? 'off';
}

export async function getDevicePushState(
	browser: PushBrowser = browserPush
): Promise<DevicePushState> {
	try {
		const found = await inspectBrowser(browser);
		if (typeof found === 'string') {
			return 'off';
		}
		return 'on';
	} catch {
		return 'unknown';
	}
}

export async function pushShowsOverOpenApp(browser: PushBrowser = browserPush): Promise<boolean> {
	if (!browser.isSupported() || !browser.showsPushItself()) {
		return false;
	}
	return (await getDevicePushState(browser)) === 'on';
}

export async function unsubscribeDevicePush(browser: PushBrowser = browserPush): Promise<void> {
	if (!browser.isSupported()) {
		return;
	}
	try {
		const subscription = await browser.getSubscription();
		await subscription?.unsubscribe();
	} catch (error) {
		Sentry.captureException(error, { tags: { source: 'push-unsubscribe' } });
	}
}

interface PushDeviceOptions {
	backend: PushBackend;
	vapidKey: string;
	browser?: PushBrowser;
}

export class PushDevice {
	state = $state<PushDeviceState>('unknown');
	isBusy = $state(true);

	readonly #backend: PushBackend;
	readonly #vapidKey: string;
	readonly #browser: PushBrowser;

	constructor({ backend, vapidKey, browser = browserPush }: PushDeviceOptions) {
		this.#backend = backend;
		this.#vapidKey = vapidKey;
		this.#browser = browser;
	}

	async refresh() {
		this.isBusy = true;
		try {
			const found = await inspectBrowser(this.#browser);
			if (typeof found === 'string') {
				this.state = found;
				return;
			}
			this.state = (await this.#backend.isRegistered(found.endpoint)) ? 'on' : 'off';
		} catch (error) {
			console.error('Error checking push subscription:', error);
			this.state = 'unknown';
		} finally {
			this.isBusy = false;
		}
	}

	toggle(): Promise<PushToggleOutcome> {
		return this.state === 'on' ? this.#disable() : this.#enable();
	}

	async #disable(): Promise<PushToggleOutcome> {
		this.isBusy = true;
		try {
			const subscription = await this.#browser.getSubscription();
			if (subscription) {
				await this.#backend.unregister(subscription.endpoint).catch((error: unknown) => {
					console.error('Failed to remove subscription from server:', error);
				});
				await subscription.unsubscribe();
			}
			this.state = 'off';
			return 'disabled';
		} catch (error) {
			console.error('Failed to unsubscribe', error);
			return 'disable-failed';
		} finally {
			this.isBusy = false;
		}
	}

	async #enable(): Promise<PushToggleOutcome> {
		if (this.state === 'unsupported' || !this.#browser.isSupported()) {
			return 'unsupported';
		}

		this.isBusy = true;
		let browserSubscribed = false;
		try {
			if (!this.#vapidKey) {
				Sentry.captureMessage('Push subscribe blocked: missing VAPID key', {
					level: 'warning',
					tags: { push_outcome: 'no_vapid_key' }
				});
				return 'unavailable';
			}

			const refusal = await this.#ensurePermission();
			if (refusal) return refusal;

			const subscription = await this.#browser.subscribe(this.#vapidKey);
			browserSubscribed = true;
			return await this.#register(subscription);
		} catch (error: unknown) {
			console.error('Failed to subscribe:', error);
			Sentry.captureException(error, {
				tags: { push_outcome: browserSubscribed ? 'backend_request_threw' : 'subscribe_threw' }
			});
			return 'failed';
		} finally {
			this.isBusy = false;
		}
	}

	async #ensurePermission(): Promise<PushToggleOutcome | null> {
		const current = this.#browser.permission();
		if (current === 'denied') {
			this.state = 'blocked';
			return 'blocked';
		}
		if (current !== 'default') return null;

		const permission = await this.#browser.requestPermission();
		if (permission === 'granted') return null;
		if (permission === 'denied') {
			this.state = 'blocked';
		}
		Sentry.addBreadcrumb({
			category: 'push',
			level: 'info',
			message: 'Push permission not granted',
			data: { permission }
		});
		return 'not-granted';
	}

	async #register(subscription: PushSubscription): Promise<PushToggleOutcome> {
		const { endpoint, keys } = subscription.toJSON();
		if (!endpoint || !keys?.p256dh || !keys.auth) {
			Sentry.captureMessage('Push subscribe returned an incomplete subscription', {
				level: 'warning',
				tags: { push_outcome: 'invalid_subscription' }
			});
			await this.#discard(subscription);
			return 'incomplete';
		}

		try {
			await this.#backend.register({ endpoint, p256dh: keys.p256dh, auth: keys.auth });
		} catch (error: unknown) {
			console.error('API Error:', error);
			Sentry.captureMessage('Push subscribe rejected by backend', {
				level: 'warning',
				tags: { push_outcome: 'backend_rejected' },
				extra: { code: getApiErrorCode(error) }
			});
			await this.#discard(subscription);
			return 'rejected';
		}

		this.state = 'on';
		return 'enabled';
	}

	async #discard(subscription: PushSubscription) {
		try {
			await subscription.unsubscribe();
		} catch (error) {
			console.error('Failed to roll back push subscription:', error);
		}
	}
}
