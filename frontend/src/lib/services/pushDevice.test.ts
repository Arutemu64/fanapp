import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@sentry/sveltekit', () => ({
	captureMessage: vi.fn(),
	captureException: vi.fn(),
	addBreadcrumb: vi.fn()
}));

import type { PushBrowser } from './pushBrowser.js';

import { getDevicePushState, type PushBackend, PushDevice } from './pushDevice.svelte';

function fakeSubscription(complete = true) {
	return {
		endpoint: 'https://push.example/1',
		toJSON: () => ({
			endpoint: 'https://push.example/1',
			keys: complete ? { p256dh: 'p', auth: 'a' } : undefined
		}),
		unsubscribe: vi.fn().mockResolvedValue(true)
	};
}

function fakeBrowser(overrides: Partial<PushBrowser> = {}): PushBrowser {
	return {
		isSupported: () => true,
		permission: () => 'granted',
		requestPermission: vi.fn().mockResolvedValue('granted'),
		getSubscription: vi.fn().mockResolvedValue(null),
		subscribe: vi.fn().mockResolvedValue(fakeSubscription()),
		...overrides
	};
}

function fakeBackend(overrides: Partial<PushBackend> = {}): PushBackend {
	return {
		isRegistered: vi.fn().mockResolvedValue(true),
		register: vi.fn().mockResolvedValue(undefined),
		unregister: vi.fn().mockResolvedValue(undefined),
		...overrides
	};
}

function device(browser: PushBrowser, backend = fakeBackend(), vapidKey = 'key') {
	return new PushDevice({ browser, backend, vapidKey });
}

beforeEach(() => {
	vi.spyOn(console, 'error').mockImplementation(() => {});
});

describe('getDevicePushState', () => {
	it('is off when push is unsupported or blocked', async () => {
		expect(await getDevicePushState(fakeBrowser({ isSupported: () => false }))).toBe('off');
		expect(await getDevicePushState(fakeBrowser({ permission: () => 'denied' }))).toBe('off');
	});

	it('is on with a browser subscription, off without one', async () => {
		const sub = fakeSubscription() as unknown as PushSubscription;
		expect(
			await getDevicePushState(fakeBrowser({ getSubscription: () => Promise.resolve(sub) }))
		).toBe('on');
		expect(await getDevicePushState(fakeBrowser())).toBe('off');
	});

	it('is unknown when the browser throws', async () => {
		const browser = fakeBrowser({ getSubscription: () => Promise.reject(new Error('boom')) });
		expect(await getDevicePushState(browser)).toBe('unknown');
	});
});

describe('PushDevice.refresh', () => {
	it('reports unsupported and blocked without asking the server', async () => {
		const backend = fakeBackend();
		const unsupported = device(fakeBrowser({ isSupported: () => false }), backend);
		await unsupported.refresh();
		expect(unsupported.state).toBe('unsupported');

		const blocked = device(fakeBrowser({ permission: () => 'denied' }), backend);
		await blocked.refresh();
		expect(blocked.state).toBe('blocked');
		expect(backend.isRegistered).not.toHaveBeenCalled();
	});

	it('is off when the server lost the subscription the browser holds', async () => {
		const sub = fakeSubscription() as unknown as PushSubscription;
		const push = device(
			fakeBrowser({ getSubscription: () => Promise.resolve(sub) }),
			fakeBackend({ isRegistered: vi.fn().mockResolvedValue(false) })
		);
		await push.refresh();
		expect(push.state).toBe('off');
		expect(push.isBusy).toBe(false);
	});

	it('settles as unknown when the check throws', async () => {
		const push = device(fakeBrowser({ getSubscription: () => Promise.reject(new Error('x')) }));
		await push.refresh();
		expect(push.state).toBe('unknown');
		expect(push.isBusy).toBe(false);
	});
});

describe('PushDevice.toggle (enable)', () => {
	it('subscribes and registers with the backend', async () => {
		const backend = fakeBackend();
		const push = device(fakeBrowser(), backend);
		expect(await push.toggle()).toBe('enabled');
		expect(push.state).toBe('on');
		expect(backend.register).toHaveBeenCalledWith({
			endpoint: 'https://push.example/1',
			p256dh: 'p',
			auth: 'a'
		});
	});

	it('fails fast without a VAPID key', async () => {
		const browser = fakeBrowser();
		expect(await device(browser, fakeBackend(), '').toggle()).toBe('unavailable');
		expect(browser.subscribe).not.toHaveBeenCalled();
	});

	it('reports blocked when the permission is already denied', async () => {
		const push = device(fakeBrowser({ permission: () => 'denied' }));
		expect(await push.toggle()).toBe('blocked');
		expect(push.state).toBe('blocked');
	});

	it('marks the device blocked when the user denies the prompt', async () => {
		const push = device(
			fakeBrowser({
				permission: () => 'default',
				requestPermission: vi.fn().mockResolvedValue('denied')
			})
		);
		expect(await push.toggle()).toBe('not-granted');
		expect(push.state).toBe('blocked');
	});

	it('rolls back the browser subscription when the backend rejects it', async () => {
		const sub = fakeSubscription();
		const push = device(
			fakeBrowser({ subscribe: vi.fn().mockResolvedValue(sub) }),
			fakeBackend({ register: vi.fn().mockRejectedValue(new Error('422')) })
		);
		expect(await push.toggle()).toBe('rejected');
		expect(sub.unsubscribe).toHaveBeenCalled();
		expect(push.state).not.toBe('on');
		expect(push.isBusy).toBe(false);
	});

	it('rolls back an incomplete subscription without calling the backend', async () => {
		const sub = fakeSubscription(false);
		const backend = fakeBackend();
		const push = device(fakeBrowser({ subscribe: vi.fn().mockResolvedValue(sub) }), backend);
		expect(await push.toggle()).toBe('incomplete');
		expect(sub.unsubscribe).toHaveBeenCalled();
		expect(backend.register).not.toHaveBeenCalled();
	});

	it('reports failed when the browser subscribe throws', async () => {
		const push = device(fakeBrowser({ subscribe: () => Promise.reject(new Error('no sw')) }));
		expect(await push.toggle()).toBe('failed');
		expect(push.isBusy).toBe(false);
	});
});

describe('PushDevice.toggle (disable)', () => {
	async function enabledDevice(backend: PushBackend, sub = fakeSubscription()) {
		const push = device(fakeBrowser({ getSubscription: vi.fn().mockResolvedValue(sub) }), backend);
		await push.refresh();
		expect(push.state).toBe('on');
		return push;
	}

	it('unregisters on the server, then unsubscribes locally', async () => {
		const backend = fakeBackend();
		const sub = fakeSubscription();
		const push = await enabledDevice(backend, sub);
		expect(await push.toggle()).toBe('disabled');
		expect(backend.unregister).toHaveBeenCalledWith('https://push.example/1');
		expect(sub.unsubscribe).toHaveBeenCalled();
		expect(push.state).toBe('off');
	});

	it('still unsubscribes locally when the server call fails', async () => {
		const sub = fakeSubscription();
		const push = await enabledDevice(
			fakeBackend({ unregister: vi.fn().mockRejectedValue(new Error('offline')) }),
			sub
		);
		expect(await push.toggle()).toBe('disabled');
		expect(sub.unsubscribe).toHaveBeenCalled();
	});
});
