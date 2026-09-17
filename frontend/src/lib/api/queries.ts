import type { CurrentUserDto } from '$lib/api/generated';

import { getCurrentUser } from '$lib/api/generated';
import {
	getCurrentUserQueryKey,
	getPublicConfigOptions,
	getScheduleOptions,
	getSubscriptionsOptions,
	getVotingNominationOptions,
	getVotingStatusOptions,
	listVotingNominationsOptions
} from '$lib/api/generated/@tanstack/svelte-query.gen';
import { offlineQueryOptions, onlineOnlyQueryOptions } from '$lib/api/queryClient';
import { queryOptions } from '@tanstack/svelte-query';

/**
 * The few queries that need app policy on top of the generated `*Options()`
 * helpers. Everything else passes a generated helper straight to `createQuery`.
 *
 * Each of these spreads the generated options first, so the query key still comes
 * from the spec and `invalidateQueries` can be keyed off the generated
 * `*QueryKey()` helper.
 */

/**
 * `initialPageParam` / `getNextPageParam` for the limit/offset "load more" feeds.
 *
 * The generated `*InfiniteOptions()` helpers supply the key and the fetcher and
 * pass a bare number through as the next offset, but they cannot know where a
 * given response keeps its items or when the list has run out — that is what
 * `itemsKey` and the short-page check below answer.
 */
export function offsetPagination<TKey extends string>(pageSize: number, itemsKey: TKey) {
	type Page = Record<TKey, readonly unknown[]>;

	return {
		initialPageParam: 0,
		// A short page is the last one, so there is no next offset to ask for.
		getNextPageParam: (lastPage: Page, allPages: Page[]): number | undefined => {
			if (lastPage[itemsKey].length < pageSize) return undefined;
			return allPages.reduce((total, page) => total + page[itemsKey].length, 0);
		}
	};
}

/**
 * Current session identity, where `null` is a real answer ("signed out") rather
 * than an error.
 *
 * The generated helper throws on any non-2xx, which would leave the query in an
 * error state on a perfectly normal 401 — and an errored identity query cannot be
 * told apart from "the network is down", which is exactly the distinction the
 * (protected) guard needs in order not to bounce an authenticated user to login
 * on a flaky connection. So a 401/403 resolves to `null` and only a genuine
 * failure rejects.
 *
 * `retry: false` because an auth verdict is not a transient failure worth
 * retrying, and identity gates first paint.
 */
export function currentUserQueryOptions() {
	return queryOptions({
		// The key still comes from the spec, so `getCurrentUserQueryKey()` invalidates
		// this query; only the fetcher below is ours, for the `null` case.
		queryKey: getCurrentUserQueryKey(),
		...offlineQueryOptions,
		retry: false,
		queryFn: async ({ signal }): Promise<CurrentUserDto | null> => {
			const { data, error, response } = await getCurrentUser({ signal });

			// Authoritative "not signed in" — a value, not a failure.
			if (response?.status === 401 || response?.status === 403) return null;

			// Reachable but no verdict (5xx / parse error / empty body): reject so the
			// cached identity keeps serving. Resolving `null` here would downgrade a
			// signed-in user to guest on a transient error and orphan their cached data.
			if (error || !data) {
				throw new Error('Identity request returned no verdict', { cause: error });
			}

			return data;
		}
	});
}

/**
 * Public festival config — drives the home hero's phase (before/during/after) and
 * countdown, so it must resolve for guests and offline.
 */
export function publicConfigQueryOptions() {
	return queryOptions({
		...getPublicConfigOptions(),
		...offlineQueryOptions
	});
}

/**
 * The programme. Carries no per-user data, so one cached copy serves guests and
 * every account and survives logout (see UNIVERSAL_OPERATIONS in ./queryClient).
 */
export function scheduleQueryOptions() {
	return queryOptions({
		...getScheduleOptions(),
		...offlineQueryOptions,
		select: (data) => data.schedule ?? []
	});
}

/**
 * Whether voting is open, plus the configured window. Online-only like the
 * nominations it frames, so the banner hides rather than claiming a stale state.
 */
export function votingStatusQueryOptions() {
	return queryOptions({
		...getVotingStatusOptions(),
		...onlineOnlyQueryOptions
	});
}

/** The nominations a voter can open. Online-only — see {@link votingStatusQueryOptions}. */
export function votingNominationsQueryOptions() {
	return queryOptions({
		...listVotingNominationsOptions(),
		...onlineOnlyQueryOptions,
		select: (data) => data.nominations ?? []
	});
}

/** One nomination's ballot. Online-only — see {@link votingStatusQueryOptions}. */
export function votingNominationQueryOptions(nominationCode: string) {
	return queryOptions({
		...getVotingNominationOptions({ path: { nomination_code: nominationCode } }),
		...onlineOnlyQueryOptions
	});
}

/**
 * The signed-in user's schedule subscriptions. `enabled` is the caller's call —
 * guests have none, so the schedule page gates it on identity.
 */
export function subscriptionsQueryOptions() {
	return queryOptions({
		...getSubscriptionsOptions(),
		...offlineQueryOptions,
		select: (data) => data.subscriptions ?? []
	});
}
