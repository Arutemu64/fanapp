import * as Sentry from '@sentry/sveltekit';

import { getApiErrorCode } from '#lib/api/errors.js';

import { browserPush, type PushBrowser } from './pushBrowser.js';

/**
 * - `blocked`: the browser permission is "denied" and never prompts again.
 * - `unsupported`: this browser can never receive push.
 * - `unknown`: the check itself failed; the switch stays usable.
 */
export type PushDeviceState = 'on' | 'off' | 'unknown' | 'blocked' | 'unsupported';

/** The coarse state the home and profile hub show, read from the browser alone. */
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

export interface PushRegistration {
	endpoint: string;
	p256dh: string;
	auth: string;
}

/** The server's side of a device subscription. */
export interface PushBackend {
	isRegistered: (endpoint: string) => Promise<boolean>;
	register: (registration: PushRegistration) => Promise<void>;
	unregister: (endpoint: string) => Promise<void>;
}

/** What the browser says about push, before asking the server. */
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

/**
 * Read this device's push state from the browser alone — no network, so it works
 * offline and costs nothing on the home and profile hub. It can disagree with the
 * server in one rare case (the server dropped a subscription the browser still
 * holds); the notifications page does the server round-trip and is the source of
 * truth.
 */
export async function getDevicePushState(
	browser: PushBrowser = browserPush
): Promise<DevicePushState> {
	try {
		const found = await inspectBrowser(browser);
		if (typeof found === 'string') {
			// Unsupported and blocked both mean nothing reaches this device; the
			// notifications page explains how to change that.
			return 'off';
		}
		return 'on';
	} catch {
		// A status line is not worth an error: show nothing rather than a guess.
		return 'unknown';
	}
}

interface PushDeviceOptions {
	backend: PushBackend;
	/** Build-time VAPID public key; empty when the deployment shipped without one. */
	vapidKey: string;
	browser?: PushBrowser;
}

/**
 * This device's push subscription: capability, permission, browser subscription
 * and server registration behind `state` and `toggle()`. Create one per view —
 * it holds no module-level state.
 */
export class PushDevice {
	state = $state<PushDeviceState>('unknown');
	/** True during the initial check and while a toggle is in flight. */
	isBusy = $state(true);

	readonly #backend: PushBackend;
	readonly #vapidKey: string;
	readonly #browser: PushBrowser;

	constructor({ backend, vapidKey, browser = browserPush }: PushDeviceOptions) {
		this.#backend = backend;
		this.#vapidKey = vapidKey;
		this.#browser = browser;
	}

	/** Re-read the state from the browser, confirmed against the server. */
	async refresh() {
		this.isBusy = true;
		try {
			const found = await inspectBrowser(this.#browser);
			if (typeof found === 'string') {
				this.state = found;
				return;
			}
			// The browser holds a subscription; confirm the server still knows this
			// exact endpoint, otherwise treat it as off so the user can re-register
			// (e.g. after the server lost the subscription).
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
				// Remove the matching subscription on the backend before unsubscribing
				// locally. A server failure doesn't stop the local unsubscribe.
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
		// Flips once the browser subscription exists, so the catch below can tell a
		// genuine subscribe / service-worker failure from a later backend-request throw.
		let browserSubscribed = false;
		try {
			// The key is baked in at build time, so it may be empty if push
			// notifications were not configured for this deployment.
			if (!this.#vapidKey) {
				// Deploy misconfig, not a user problem: the build shipped without a VAPID
				// key, so push can never work here. One grouped GlitchTip issue surfaces it.
				Sentry.captureMessage('Push subscribe blocked: missing VAPID key', {
					level: 'warning',
					tags: { push_outcome: 'no_vapid_key' }
				});
				return 'unavailable';
			}

			if (this.#browser.permission() === 'denied') {
				this.state = 'blocked';
				return 'blocked';
			}
			if (this.#browser.permission() === 'default') {
				const permission = await this.#browser.requestPermission();
				if (permission !== 'granted') {
					if (permission === 'denied') {
						this.state = 'blocked';
					}
					// User choice, not a bug — a breadcrumb (buffered, free) is enough to
					// give context if a real error fires later in this attempt.
					Sentry.addBreadcrumb({
						category: 'push',
						level: 'info',
						message: 'Push permission not granted',
						data: { permission }
					});
					return 'not-granted';
				}
			}

			const subscription = await this.#browser.subscribe(this.#vapidKey);
			browserSubscribed = true;

			const { endpoint, keys } = subscription.toJSON();
			if (!endpoint || !keys?.p256dh || !keys.auth) {
				// The browser handed back a subscription missing the fields the backend
				// needs — a real failure worth surfacing, not a user choice.
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
				// The browser subscribed but the backend rejected it, so push stays off
				// despite a granted permission — the failure mode worth catching.
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
		} catch (error: unknown) {
			console.error('Failed to subscribe:', error);
			// Classify by where it threw: before the browser subscription exists it's a
			// genuine subscribe / service-worker failure; after, it's a bug in handling
			// the backend registration (the request's own failure is caught above).
			Sentry.captureException(error, {
				tags: { push_outcome: browserSubscribed ? 'backend_request_threw' : 'subscribe_threw' }
			});
			return 'failed';
		} finally {
			this.isBusy = false;
		}
	}

	// Best-effort rollback of a browser push subscription. A failing unsubscribe is
	// itself a cleanup problem — it must not propagate and be reported as the
	// original failure, whose real cause was already captured at the call site.
	async #discard(subscription: PushSubscription) {
		try {
			await subscription.unsubscribe();
		} catch (error) {
			console.error('Failed to roll back push subscription:', error);
		}
	}
}
