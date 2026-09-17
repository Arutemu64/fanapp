# ADR-0018: TanStack Query owns all frontend data fetching and caching

- **Status:** Accepted
- **Date:** 2026-09-17
- **Deciders:** arutemu64

## Context

The frontend had grown two parallel data flows, and every feature had to pick one.

SvelteKit `load` functions fetched through per-context hey-api clients and
returned plain snapshots; freshness came from `depends('app:x')` +
`invalidate('app:x')`, which re-runs a `load`. Alongside that sat a hand-rolled
offline layer, `$lib/utils/offlineCache.ts`: `fetchWithCache` wrapped every
cacheable load with its own reachability check, timeout, IndexedDB read/write,
`{ value, cachedAt }` envelope, user/universal key scoping, a monotonic epoch
guard so a request in flight during logout couldn't repopulate a cleared entry,
and `warmCache` to seed an entry before first visit.

Anything that had to stay live on the _page_ then needed a third mechanism,
because a `load` snapshot doesn't update: `PaginatedFeed` for "load more",
`dedupeById` + `feedSnapshotKey` + `{#key}` remounts to splice a server page
together with SSE arrivals, and `UnreadCountService` — a class with an in-flight
latch, a coalescing pending flag, an "authoritative value" flag and a generation
counter, all to stop a badge refresh racing a mark-read.

None of that was badly written; it was correct, and the epoch guard and the
generation counter exist because the naive versions were wrong. But it was a
cache, an invalidation protocol, a request deduplicator and a pagination engine,
written by hand, with the _same_ datum reachable through two paths that could
disagree: a page's `load` snapshot and a component's local state.

## Decision

We will route **every** network read through a single **TanStack Query**
(`@tanstack/svelte-query` v6, Svelte 5 runes) cache, and delete the custom layers.

- **Keys and fetchers come from the spec.** The `@tanstack/svelte-query` plugin
  for `@hey-api/openapi-ts` generates `<operation>Options()`,
  `<operation>QueryKey()`, `<operation>InfiniteOptions()` and
  `<operation>Mutation()`, which are passed straight into the standard hooks.
  App policy (nullable identity, offline options, a `select`) is composed on top
  in `$lib/api/queries.ts`, always spreading the generated options first so the
  key still comes from the spec.
- **Components own reads** via `createQuery` / `createInfiniteQuery`. A `load`
  fetches only what the _route_ must decide — a permission guard, a redirect, an
  error page, a page title — and does it with `ensureQueryData`, warming the very
  entry the component then reads. One request, one cache, no second flow.
- **Offline is the persister.** The cache is dehydrated to IndexedDB through
  `@tanstack/query-persist-client-core` + `idb-keyval`, restored **before** the
  first route load runs. Two allowlists replace the per-call key scoping:
  `PERSISTED_OPERATIONS` (what reaches disk) and `UNIVERSAL_OPERATIONS` (what
  survives logout); anything unlisted is memory-only and user-scoped, so a new
  endpoint cannot leak by omission. `clearUserQueries` replaces `clearUserCache`.
- **Invalidation replaces `invalidate()`.** `depends`/`invalidate` and
  `invalidateAll` are gone; mutations and SSE events call
  `queryClient.invalidateQueries({ queryKey: <generated>QueryKey() })`.
- **The QueryClient is per-boot, on layout data** — built in the root
  `+layout.ts`, never a `$lib` module singleton, because it holds the viewer's
  data and a module outlives login/logout in this SPA (AGENTS.md).

## Consequences

- Roughly 600 lines of bespoke caching, pagination and state-sync logic are
  deleted: `offlineCache.ts` (+ its tests), `services/feed.svelte.ts`,
  `utils/feed.ts`, `services/unreadCount.svelte.ts` (+ its tests), and the
  streamed notification seed on the `(app)` layout.
- New runtime dependencies: `@tanstack/svelte-query` and
  `@tanstack/query-persist-client-core`. `idb-keyval` stays, now behind the
  persister rather than a hand-written store.
- **The epoch guard's invariant is now structural.** It existed because a
  user-scoped write could land after logout; `clearUserQueries` removes the
  queries themselves and an in-flight fetch has nowhere to write back to.
- **The badge can lag a mutation by a round-trip**, as it did before — invalidation
  is still a refetch, and we still refuse an optimistic delta (an increment and an
  authoritative total cannot be ordered without an "as-of" token the endpoint
  doesn't return).
- Loads no longer inject SvelteKit's `fetch`. It exists for SSR inlining and
  `invalidate()`, and this app is `ssr = false` with invalidation owned by the
  cache; cookies ride on `credentials: 'include'` regardless.
- There is now **one** hey-api client, the configured generated singleton. This
  reverses the "never use a module-global client" rule from
  [ADR-0017](0017-hey-api-for-the-frontend-api-client.md), which stands on
  everything else: that rule was about _state_ bleeding across navigation and
  login/logout, and the client now holds none — only a base URL, a cookie policy
  and two interceptors. The state it was protecting moved into the QueryClient,
  which is explicitly per-boot and cleared on logout.

## Alternatives considered

- **Keep `load` + `fetchWithCache`, fix the seams case by case.** Rejected: the
  dual flow _is_ the defect. Every new live surface would keep re-deriving
  deduplication, coalescing and cache invalidation by hand, and the two paths to
  one datum could still disagree.
- **TanStack Query for reads, keep `invalidate()` for page data.** Rejected: that
  keeps both flows and adds a third rule about which to use when. An invalidated
  query and a re-run `load` would race on the same datum.
- **Keep loads as the only fetch site, with `ensureQueryData` everywhere.** Tempting,
  and far less churn — but a `load` returns a snapshot, so `invalidateQueries`
  would update the cache without re-rendering the page, and we would be back to
  pairing it with `invalidate()`.
- **A thin wrapper over TanStack Query** (a `createCachedQuery` helper). Rejected:
  it is how the last abstraction started. Vanilla `queryKey` / `staleTime` /
  `invalidateQueries` are what the documentation, the error messages and every
  future contributor already know.
