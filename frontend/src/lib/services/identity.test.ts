import { QueryClient } from '@tanstack/svelte-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { CurrentUserDto } from '#lib/api/generated/index.js';

import { fakeStorage } from '#lib/testing/storage.js';

import {
	currentUserOptions,
	flushPendingLogout,
	isLogoutPending,
	markLogoutPending,
	settleIdentityForBoot
} from './identity.js';

const getCurrentUser = vi.hoisted(() => vi.fn());
const logoutUser = vi.hoisted(() => vi.fn());
vi.mock('#lib/api/generated/index.js', () => ({ getCurrentUser, logoutUser }));

const USER = { id: '1', username: 'neko' } as CurrentUserDto;

beforeEach(() => {
	vi.stubGlobal('localStorage', fakeStorage());
	getCurrentUser.mockReset();
	logoutUser.mockReset();
	getCurrentUser.mockResolvedValue({ data: USER, response: { ok: true, status: 200 } });
});

describe('flushPendingLogout', () => {
	it('sends nothing when no logout is pending', async () => {
		await flushPendingLogout();

		expect(logoutUser).not.toHaveBeenCalled();
	});

	it('clears the intent once the revoke succeeds', async () => {
		logoutUser.mockResolvedValue({ response: { ok: true, status: 204 } });
		markLogoutPending();

		await flushPendingLogout();

		expect(logoutUser).toHaveBeenCalledOnce();
		expect(isLogoutPending()).toBe(false);
	});

	it('clears the intent on a 401, since the session is already gone', async () => {
		logoutUser.mockResolvedValue({ response: { ok: false, status: 401 } });
		markLogoutPending();

		await flushPendingLogout();

		expect(isLogoutPending()).toBe(false);
	});

	it('keeps the intent on a 5xx, so the next reconnect retries', async () => {
		logoutUser.mockResolvedValue({ response: { ok: false, status: 503 } });
		markLogoutPending();

		await flushPendingLogout();

		expect(isLogoutPending()).toBe(true);
	});

	it('keeps the intent while the backend gives no answer, so the next reconnect retries', async () => {
		logoutUser.mockResolvedValue({ error: new TypeError('Failed to fetch'), response: undefined });
		markLogoutPending();

		await flushPendingLogout();

		expect(isLogoutPending()).toBe(true);
	});
});

describe('currentUserOptions', () => {
	it('answers guest without asking /me while a logout is pending, so the cookie cannot restore the account', async () => {
		markLogoutPending();
		const queryClient = new QueryClient();

		await expect(queryClient.query(currentUserOptions())).resolves.toBeNull();

		expect(getCurrentUser).not.toHaveBeenCalled();
	});
});

describe('settleIdentityForBoot', () => {
	it('trusts a restored user without a request', async () => {
		const queryClient = new QueryClient();
		queryClient.setQueryData(currentUserOptions().queryKey, USER);

		await settleIdentityForBoot(queryClient);

		expect(getCurrentUser).not.toHaveBeenCalled();
	});

	it('re-checks a restored user once a logout is pending, since the cache may predate it', async () => {
		markLogoutPending();
		const queryClient = new QueryClient();
		queryClient.setQueryData(currentUserOptions().queryKey, USER);

		await settleIdentityForBoot(queryClient);

		expect(queryClient.getQueryData(currentUserOptions().queryKey)).toBeNull();
	});

	it('re-checks a restored guest, who may be back from a social login', async () => {
		const queryClient = new QueryClient();
		queryClient.setQueryData(currentUserOptions().queryKey, null);

		await settleIdentityForBoot(queryClient);

		expect(queryClient.getQueryData(currentUserOptions().queryKey)).toEqual(USER);
	});
});
