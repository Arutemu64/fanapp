import {
	getPublicConfigQueryKey,
	getScheduleQueryKey
} from '$lib/api/generated/@tanstack/svelte-query.gen';
import { describe, expect, it } from 'vitest';

import { clearUserQueries, createQueryClient } from './queryClient';

/**
 * The scoping policy is ours, not TanStack's: which cached operations survive a
 * logout. Getting it wrong leaks one account's data to the next on a shared
 * device, and nothing else in the app would notice.
 */
describe('clearUserQueries', () => {
	it('drops user-scoped entries and keeps universal ones', () => {
		const queryClient = createQueryClient();

		// Universal: carries no identity, so it serves guests and every account.
		queryClient.setQueryData(getScheduleQueryKey(), { schedule: [] });
		queryClient.setQueryData(getPublicConfigQueryKey(), { festival_start: '', festival_end: '' });
		// The viewer's own data.
		queryClient.setQueryData([{ _id: 'getSubscriptions', baseUrl: '/api' }], { subscriptions: [] });

		clearUserQueries(queryClient);

		expect(queryClient.getQueryData(getScheduleQueryKey())).toBeDefined();
		expect(queryClient.getQueryData(getPublicConfigQueryKey())).toBeDefined();
		expect(
			queryClient.getQueryData([{ _id: 'getSubscriptions', baseUrl: '/api' }])
		).toBeUndefined();
	});

	it("treats an unrecognized operation as the viewer's own", () => {
		const queryClient = createQueryClient();
		// A new endpoint nobody added to UNIVERSAL_OPERATIONS must not survive logout
		// by omission — the default has to fail closed.
		queryClient.setQueryData([{ _id: 'someBrandNewEndpoint', baseUrl: '/api' }], { rows: [] });

		clearUserQueries(queryClient);

		expect(
			queryClient.getQueryData([{ _id: 'someBrandNewEndpoint', baseUrl: '/api' }])
		).toBeUndefined();
	});
});
