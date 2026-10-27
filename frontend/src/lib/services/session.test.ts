import { QueryClient, QueryObserver } from '@tanstack/svelte-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { CurrentUserDto } from '#lib/api/generated/index.js';

import { currentUserOptions, isLogoutPending, markLogoutPending } from '#lib/services/identity.js';
import { fakeStorage } from '#lib/testing/storage.js';

import { Session, type SessionRouter } from './session.js';

const getCurrentUser = vi.hoisted(() => vi.fn());
const logoutUser = vi.hoisted(() => vi.fn());
vi.mock('#lib/api/generated/index.js', () => ({ getCurrentUser, logoutUser }));

const USER = { id: '1', username: 'neko' } as CurrentUserDto;

function setup({ reachable = true } = {}) {
	const queryClient = new QueryClient();
	const calls: string[] = [];
	const events = { restart: vi.fn(() => void calls.push('restart')) };
	const step = (name: string) =>
		vi.fn(() => {
			calls.push(name);
			return Promise.resolve();
		});
	const goHome = step('goHome');
	const router: SessionRouter = {
		goToLoginTarget: step('goToLoginTarget'),
		goHome,
		redirectToLogin: step('redirectToLogin')
	};
	const unsubscribePush = step('unsubscribePush');
	const session = new Session({
		queryClient,
		events,
		router,
		isReachable: () => reachable,
		unsubscribePush
	});
	const userKey = currentUserOptions().queryKey;
	queryClient.setQueryData(userKey, null);
	new QueryObserver(queryClient, { ...currentUserOptions(), staleTime: Infinity }).subscribe(
		() => {}
	);
	return { queryClient, events, goHome, unsubscribePush, session, userKey, calls };
}

beforeEach(() => {
	vi.stubGlobal('localStorage', fakeStorage());
	getCurrentUser.mockReset();
	logoutUser.mockReset();
});

describe('Session.loggedIn', () => {
	it('loads the new identity before navigating, then redials the stream', async () => {
		getCurrentUser.mockResolvedValue({ data: USER, response: { status: 200 } });
		const { queryClient, session, userKey, calls } = setup();
		queryClient.setQueryData(userKey, null);

		await session.loggedIn();

		expect(queryClient.getQueryData(userKey)).toEqual(USER);
		expect(calls).toEqual(['goToLoginTarget', 'restart']);
	});

	it('joins the /me/ refetch its invalidation starts instead of aborting it for a second one', async () => {
		getCurrentUser.mockResolvedValue({ data: USER, response: { status: 200 } });
		const { session } = setup();

		await session.loggedIn();

		expect(getCurrentUser).toHaveBeenCalledOnce();
	});

	it('cancels a logout queued offline so the reconnect flush cannot revoke the new session', async () => {
		getCurrentUser.mockResolvedValue({ data: USER, response: { status: 200 } });
		markLogoutPending();
		const { session } = setup();

		await session.loggedIn();

		expect(isLogoutPending()).toBe(false);
	});
});

describe('Session.logOut', () => {
	it('revokes on the server, then shows the guest state and redials the stream', async () => {
		const { queryClient, session, userKey, calls } = setup();
		queryClient.setQueryData(userKey, USER);
		const revoke = vi.fn(() => {
			calls.push('revoke');
			return Promise.resolve();
		});

		await session.logOut(revoke);

		expect(queryClient.getQueryData(userKey)).toBeNull();
		expect(calls).toEqual(['revoke', 'goHome', 'restart', 'unsubscribePush']);
		expect(isLogoutPending()).toBe(false);
	});

	it('forgets the account data that no screen uses', async () => {
		const { queryClient, session, userKey } = setup();
		queryClient.setQueryData(userKey, USER);
		queryClient.setQueryData(['notifications'], [{ id: 1 }]);

		await session.logOut(() => Promise.resolve());

		expect(queryClient.getQueryData(['notifications'])).toBeUndefined();
	});

	it('leaves everything as it was when the server refuses', async () => {
		const { queryClient, session, userKey, events, goHome, unsubscribePush } = setup();
		queryClient.setQueryData(userKey, USER);

		await expect(session.logOut(() => Promise.reject(new Error('boom')))).rejects.toThrow('boom');

		expect(queryClient.getQueryData(userKey)).toEqual(USER);
		expect(goHome).not.toHaveBeenCalled();
		expect(events.restart).not.toHaveBeenCalled();
		expect(unsubscribePush).not.toHaveBeenCalled();
	});

	it('offline: records the intent instead of calling the server, and still tears down', async () => {
		const { queryClient, session, userKey, events, unsubscribePush } = setup({
			reachable: false
		});
		queryClient.setQueryData(userKey, USER);
		const revoke = vi.fn();

		await session.logOut(revoke);

		expect(revoke).not.toHaveBeenCalled();
		expect(isLogoutPending()).toBe(true);
		expect(queryClient.getQueryData(userKey)).toBeNull();
		expect(events.restart).toHaveBeenCalledOnce();
		expect(unsubscribePush).toHaveBeenCalledOnce();
	});
});

describe('Session.expired', () => {
	it('flips to guest, leaves the protected screen, and redials the stream as the guest', async () => {
		const { queryClient, session, userKey, calls } = setup();
		queryClient.setQueryData(userKey, USER);

		await session.expired();

		expect(queryClient.getQueryData(userKey)).toBeNull();
		expect(calls).toEqual(['redirectToLogin', 'restart', 'unsubscribePush']);
	});

	it('ends only once for a burst of 401s, and not at all for a guest', async () => {
		const { queryClient, session, userKey, events } = setup();
		queryClient.setQueryData(userKey, USER);

		await Promise.all([session.expired(), session.expired(), session.expired()]);
		await session.expired();

		expect(events.restart).toHaveBeenCalledOnce();
	});
});

describe('Session.settlePendingLogout', () => {
	it('revokes the old session before a social login, so the boot flush cannot end the new one', async () => {
		logoutUser.mockResolvedValue({ response: { ok: true, status: 204 } });
		markLogoutPending();
		const { session } = setup();

		await expect(session.settlePendingLogout()).resolves.toBe(true);

		expect(logoutUser).toHaveBeenCalledOnce();
		expect(session.logoutPending).toBe(false);
	});

	it('keeps the intent when the revoke fails, so an abandoned login cannot restore the old account', async () => {
		logoutUser.mockResolvedValue({ response: { ok: false, status: 503 } });
		markLogoutPending();
		const { session } = setup();

		await expect(session.settlePendingLogout()).resolves.toBe(false);

		expect(session.logoutPending).toBe(true);
	});

	it('gives up on a stalled revoke and keeps the intent, so the user can retry', async () => {
		logoutUser.mockResolvedValue({
			error: new DOMException('signal timed out', 'TimeoutError'),
			response: undefined
		});
		markLogoutPending();
		const { session } = setup();

		await expect(session.settlePendingLogout()).resolves.toBe(false);

		const [options] = logoutUser.mock.lastCall as [{ signal?: AbortSignal }];
		expect(options.signal).toBeInstanceOf(AbortSignal);
		expect(session.logoutPending).toBe(true);
	});
});
