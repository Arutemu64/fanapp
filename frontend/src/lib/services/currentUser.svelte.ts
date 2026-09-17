import type { CurrentUserDto } from '$lib/api/generated';
import type { QueryClient } from '@tanstack/svelte-query';

import { currentUserQueryOptions } from '$lib/api/queries';
import { createQuery } from '@tanstack/svelte-query';
import { getContext, setContext } from 'svelte';

/**
 * The signed-in user, read reactively from the query cache.
 *
 * Identity is resolved in the root layout's `load` (the (protected) guard has to
 * decide before a route renders), but every *component* reads it from here so a
 * 401 interceptor refetch or an explicit logout updates the whole app at once,
 * with no route re-run. Held in Svelte context, never a module singleton — it is
 * user-scoped state, and a module outlives login/logout in this SPA.
 */

const CURRENT_USER_KEY = Symbol('currentUser');

export interface CurrentUserContext {
	/** `null` for a guest, and while identity is unknown (offline cold boot). */
	readonly current: CurrentUserDto | null;
	/** True while the first identity resolution is still in flight. */
	readonly loading: boolean;
}

export function setCurrentUserContext(queryClient: QueryClient): CurrentUserContext {
	const query = createQuery(currentUserQueryOptions, () => queryClient);

	const context: CurrentUserContext = {
		get current() {
			return query.data ?? null;
		},
		get loading() {
			return query.isPending;
		}
	};

	return setContext(CURRENT_USER_KEY, context);
}

export function getCurrentUserContext(): CurrentUserContext {
	const context = getContext<CurrentUserContext | undefined>(CURRENT_USER_KEY);
	if (!context) {
		throw new Error('getCurrentUserContext() called outside the root layout');
	}
	return context;
}
