import { QueryClient } from '@tanstack/svelte-query';

/**
 * The shared `QueryClient` — a module-level singleton, deliberately.
 *
 * This looks like exactly what docs/api.md ("Client Isolation") bans, but that
 * rule targets a *transport* client whose middleware carries mutable
 * per-request latches. A `QueryClient` is a cache container, not a transport —
 * the same shape as `cacheStore` in `$lib/utils/offlineCache.ts`, which is
 * *also* a module singleton for the same reason: a shared cache is the point,
 * and isolation across login/logout is achieved by explicitly clearing the
 * user-scoped entries on logout (`clearUserCache`), not by recreating the whole
 * store. A single `QueryClient` is what lets a `load` function
 * (`queryClient.ensureQueryData(...)`) and its page's `createQuery` read the
 * same cache — constructing a fresh instance per component would defeat that,
 * and a `load` runs before the root layout component exists on first boot
 * anyway, so a component-scoped instance can't be reached from `load` at all.
 *
 * See docs/sketches/hey-api-tanstack-query-migration.md §1.
 *
 * ⚠️ A query that caches per-user data (identity, own subscriptions,
 * notifications) MUST clear its query key(s) wherever `clearUserCache()` runs
 * today (logout, session-expiry reconciliation) — e.g.
 * `queryClient.removeQueries({ queryKey: ['me'] })` — or that data survives a
 * logout on a shared device. `tools/settings` (the first page on this stack)
 * holds festival-wide config, not personal data, so this doesn't apply yet.
 */
export const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			retry: 1
		}
	}
});
