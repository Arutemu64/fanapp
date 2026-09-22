# ADR-0018: TanStack Query owns all frontend data fetching and caching

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** arutemu64

## Context

The frontend had grown two parallel data paths. Reads worth showing offline went
through `fetchWithCache` — a hand-rolled IndexedDB layer (~265 lines) with its
own key scoping, staleness envelope, first-paint timeout and a logout epoch
guard. Everything else called the generated SDK directly from a component and
kept whatever state it needed alongside. Freshness was coordinated by a third
mechanism, SvelteKit's `depends()`/`invalidate('app:*')`, across eight keys.

Around that sat more bespoke machinery, each piece solving a problem a query
library already solves: `PaginatedFeed` (offset pagination with manual dedupe),
`UnreadCountService` (a coalescing, generation-guarded refresh loop for one
number), `warmCache` (an "is it already cached?" prefetch), and a health-endpoint
reachability probe with a confirm window and backoff polling, whose result gated
whether a `load` should even attempt a request.

The cost was not the line count but the seams. The same data could be fresh in
one surface and stale in another — the bell's badge and the notifications page
each reconciled the unread count their own way. A mutation had to remember which
of several mechanisms to poke. Adding a screen meant re-deciding how it caches.

## Decision

We will route **all** network reads and cached data through TanStack Query
(`@tanstack/svelte-query` v6, the runes adapter), driven by the Hey API
`@tanstack/svelte-query` plugin's generated `*Options()` / `*QueryKey()` /
`*Mutation()` helpers, which extends [ADR-0017](0017-hey-api-for-the-frontend-api-client.md).

- **One QueryClient**, created per app boot in the root `+layout.ts` and passed
  down as `data.queryClient` — never a module singleton, because it holds the
  signed-in user's data and modules outlive login/logout in this SPA.
- **Loads prefetch, components read.** Routes keep their `load` (guards,
  nav-blocking, error pages, route params) but only call `prefetchQuery`; the
  component reads the same generated options with `createQuery`.
- **Offline is the persisted cache**: the whole client is dehydrated to
  IndexedDB via `@tanstack/query-persist-client-core` + `idb-keyval` and
  restored before children render. `gcTime` is 24h so a query survives to the
  next boot, and `networkMode: 'offlineFirst'` so a route renders its saved copy
  and still attempts the network.
- **Voting stays uncached** (`gcTime: 0`): a ballot you cannot submit is a dead
  end, not offline content.
- **Connectivity is `onlineManager`**, the same signal that gates queries.
- **One invalidation mechanism.** `depends()`/`invalidate('app:*')` is removed;
  SSE events and mutations call `invalidateQueries` with a generated key.

Deleted: `offlineCache`, `reachability`, `reachabilityTransition`,
`fetchTimeout`, `PaginatedFeed`, `UnreadCountService` and their helpers.

## Consequences

Adding a screen is now a generated `*Options()` call; caching, deduplication,
pagination and offline persistence come with it. A mutation reconciles by
invalidating the keys it moved, and every surface reading those keys updates
together — the bell badge and the notifications page cannot drift apart.

Two capabilities were knowingly given up:

- **Server reachability is now `navigator.onLine`.** The deleted probe existed
  because `navigator.onLine` reports online on a captive portal or a
  connected-but-dead VPN. The app no longer distinguishes "no internet" from
  "server unreachable", and its copy no longer claims to. Restoring the
  distinction means feeding a probe into `onlineManager.setEventListener`, not
  reviving a parallel reachability module.
- **Logout clears the whole cache.** The old cache scoped entries into per-user
  and universal, wiping only the former. One persister dehydrates one blob, so
  `queryClient.clear()` + `persister.removeClient()` takes the public schedule
  and config with it: a guest on a shared device right after a logout boots
  offline to empty states until they reconnect. Splitting it again means a
  `shouldDehydrateQuery` filter over two stores.

Follow-on obligations: `persistOptions.maxAge` must never exceed `gcTime`; only
one idb-keyval database may be opened (two racing opens leave the second
permanently unusable in Firefox); and the generated `*InfiniteOptions()` helpers
carry no page params, so each feed keeps a single shared builder in
`$lib/api/feeds.ts` rather than letting a load and a component drift.

The superseded `fanfan-cache` database is dropped once on the first boot after
upgrade — nothing else would ever clear the previous account's rows from an
installed device again. That cleanup can be removed a release or two after this
ships.

## Alternatives considered

**Keep the custom cache, adopt TanStack Query for fetching only.** Rejected: two
caches is the problem this change exists to remove, and the custom layer's value
(scoped logout wipes) is a smaller property than a single coherent invalidation
graph.

**Move every fetch into components and delete the loads.** Rejected: the loads
carry permission guards, `error(403)`/`redirect` behaviour and route params that
a component-level fetch would have to re-implement, and it would rewrite every
loading and error surface in the app for no caching benefit.
