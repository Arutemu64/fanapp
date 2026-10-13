import { QueryClient, QueryObserver } from '@tanstack/svelte-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { CurrentUserDto } from '#lib/api/generated/index.js';

import { currentUserOptions } from '#lib/api/index.js';
import { fakeStorage } from '#lib/testing/storage.js';
import { isLogoutPending, markLogoutPending } from '#lib/utils/pendingLogout.js';

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
	const session = new Session({ queryClient, events, router, isReachable: () => reachable });
	const userKey = currentUserOptions().queryKey;
	// The root layout always observes the user query, so forgetting inactive
	// queries never removes it.
	// Seeded and fresh, so subscribing doesn't fetch over what a test sets.
	queryClient.setQueryData(userKey, null);
	new QueryObserver(queryClient, { ...currentUserOptions(), staleTime: Infinity }).subscribe(
		() => {}
	);
	return { queryClient, events, goHome, session, userKey, calls };
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
		expect(calls).toEqual(['revoke', 'goHome', 'restart']);
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
		const { queryClient, session, userKey, events, goHome } = setup();
		queryClient.setQueryData(userKey, USER);

		await expect(session.logOut(() => Promise.reject(new Error('boom')))).rejects.toThrow('boom');

		expect(queryClient.getQueryData(userKey)).toEqual(USER);
		expect(goHome).not.toHaveBeenCalled();
		expect(events.restart).not.toHaveBeenCalled();
	});

	it('offline: records the intent instead of calling the server, and still tears down', async () => {
		const { queryClient, session, userKey, events } = setup({ reachable: false });
		queryClient.setQueryData(userKey, USER);
		const revoke = vi.fn();

		await session.logOut(revoke);

		expect(revoke).not.toHaveBeenCalled();
		expect(isLogoutPending()).toBe(true);
		expect(queryClient.getQueryData(userKey)).toBeNull();
		expect(events.restart).toHaveBeenCalledOnce();
	});
});

describe('Session.expired', () => {
	it('flips to guest, leaves the protected screen, and redials the stream as the guest', async () => {
		const { queryClient, session, userKey, calls } = setup();
		queryClient.setQueryData(userKey, USER);

		await session.expired();

		expect(queryClient.getQueryData(userKey)).toBeNull();
		expect(calls).toEqual(['redirectToLogin', 'restart']);
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
});
