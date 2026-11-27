import { type QueryClient, queryOptions } from '@tanstack/svelte-query';

import { getCurrentUserQueryKey } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { getCurrentUser, logout } from '#lib/api/generated/index.js';
import { queryForLoad } from '#lib/api/index.js';
import { readStorage, removeStorage, writeStorage } from '#lib/utils/safeStorage.js';

const PENDING_LOGOUT_KEY = 'fanfan:pending-logout';

export function markLogoutPending(): void {
	writeStorage('local', PENDING_LOGOUT_KEY, '1');
}

export function isLogoutPending(): boolean {
	return readStorage('local', PENDING_LOGOUT_KEY) === '1';
}

export function clearLogoutPending(): void {
	removeStorage('local', PENDING_LOGOUT_KEY);
}

export async function flushPendingLogout(signal?: AbortSignal): Promise<void> {
	if (!isLogoutPending()) return;

	const { response } = await logout({ signal });
	if (response?.ok || response?.status === 401 || response?.status === 403) {
		clearLogoutPending();
	}
}

export function currentUserOptions() {
	return queryOptions({
		queryKey: getCurrentUserQueryKey(),
		queryFn: async ({ signal }) => {
			if (isLogoutPending()) return null;

			const { data, error, response } = await getCurrentUser({ signal });
			if (response?.status === 401 || response?.status === 403) return null;
			if (data === undefined) {
				// eslint-disable-next-line @typescript-eslint/only-throw-error -- the API error body is a plain object
				throw error;
			}
			return data;
		}
	});
}

export async function settleIdentityForBoot(queryClient: QueryClient): Promise<void> {
	const options = currentUserOptions();
	if (isLogoutPending()) {
		queryClient.setQueryData(options.queryKey, null);
		return;
	}

	const cachedUser = queryClient.getQueryData(options.queryKey);
	if (cachedUser) return;
	if (cachedUser === null) {
		// A social login can return with a new cookie and a saved guest result.
		queryClient.removeQueries({ queryKey: options.queryKey, exact: true });
	}

	await queryForLoad(queryClient, options).catch(() => {});
}
