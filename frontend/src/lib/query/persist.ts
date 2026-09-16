import type { QueryMeta } from '@tanstack/svelte-query';

/**
 * Whether a persisted query belongs to the signed-in user or to everyone.
 *
 * Mirrors the scopes the identity cache uses (`$lib/utils/offlineCache.ts`):
 * `user` entries are dropped on logout so one account's data can never surface
 * for the next on a shared device; `universal` entries (the public schedule, the
 * festival config) survive logout and serve guests and the next account alike.
 */
export type PersistScope = 'universal' | 'user';

const PERSIST_SCOPE_META_KEY = 'persistScope';

/** Anything carrying query options we can tag — the generated `*Options()` results. */
interface TaggableQueryOptions {
	meta?: QueryMeta;
}

/**
 * Opt a query into IndexedDB persistence under `scope`.
 *
 * Persistence is opt-in, not the default: the dehydrate filter in
 * `persister.ts` writes only the queries tagged here, so an admin tool or a
 * voting ballot can never end up readable offline just by being fetched. Wrap
 * the generated options at the call site:
 *
 * ```ts
 * createQuery(() => persisted(getScheduleOptions({ client }), 'universal'));
 * ```
 */
export function persisted<T extends TaggableQueryOptions>(options: T, scope: PersistScope): T {
	return {
		...options,
		meta: { ...options.meta, [PERSIST_SCOPE_META_KEY]: scope }
	};
}

/** The scope a query was tagged with, or `undefined` when it opted out of persistence. */
export function persistScopeOf(meta: QueryMeta | undefined): PersistScope | undefined {
	const scope = meta?.[PERSIST_SCOPE_META_KEY];
	return scope === 'user' || scope === 'universal' ? scope : undefined;
}
