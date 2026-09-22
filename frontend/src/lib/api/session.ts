import type { CurrentUserDto } from '$lib/api/generated';

import { getCurrentUser } from '$lib/api/generated';
import { getCurrentUserQueryKey } from '$lib/api/generated/@tanstack/svelte-query.gen';
import { queryOptions } from '@tanstack/svelte-query';

/**
 * The signed-in user, or `null` for a guest.
 *
 * Hand-written rather than the generated `getCurrentUserOptions()` only to
 * reinterpret the endpoint's auth verdict: `/me/` answers 401/403 for a guest,
 * which the generated `queryFn` would throw (`throwOnError`) and which the
 * generated type forbids resolving as `null`. Being logged out is a normal,
 * cacheable answer, not a failure — as an error it would never persist, so an
 * offline boot could not tell "guest" from "unknown" and would keep retrying a
 * request that cannot succeed.
 *
 * The generated query key is reused verbatim, so `getCurrentUserQueryKey()`
 * invalidates this query from anywhere (see `attachSessionReconciler`).
 */
export function currentUserQueryOptions() {
	return queryOptions({
		queryFn: async ({ signal }): Promise<CurrentUserDto | null> => {
			const { data, error, response } = await getCurrentUser({ signal });

			// Authoritative "not signed in" — cache it as the guest state.
			if (response?.status === 401 || response?.status === 403) return null;
			// The API error payload, not an Error: every consumer (getApiErrorDetail,
			// throwApiError) reads `code`/`details` off it, and this is exactly what the
			// generated `throwOnError` queryFns throw, so the two stay interchangeable.
			// eslint-disable-next-line @typescript-eslint/only-throw-error
			if (error) throw error;

			return data ?? null;
		},
		queryKey: getCurrentUserQueryKey(),
		// A 5xx or a parse error must surface as an error so the cached identity is
		// kept rather than downgraded; retrying it would only delay that fallback.
		retry: false
	});
}
